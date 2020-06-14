import os
import json
import copy
import re
import glob
import shutil
from enum import Enum
from moviepy.editor import VideoFileClip, concatenate_videoclips


class QuestionType(Enum):
    SINGLE_CHOICE = 1
    MULTIPLE_CHOICES = 2


class Question:

    question: str
    choices: list
    answers: list

    def __init__(self, question: str, choices: list, answers: list):
        self.question = question
        self.choices = choices
        self.answers = answers


class SingleChoiceQuestion(Question):

    questionType: QuestionType

    def __init__(self, question: str, choices: list, answer: str):
        self.question = question
        self.choices = choices
        self.answers.append(answer)
        self.questionType = QuestionType.SINGLE_CHOICE


class MultipleChoicesQuestion(Question):

    questionType: QuestionType

    def __init__(self, question: str, choices: list, answers: list):
        self.question = question
        self.choices = choices
        self.answers = answers
        self.questionType = QuestionType.MULTIPLE_CHOICES

# Question set per video.
class QuestionSet:

    questions: list
    # Could get duration of time stamp of the first question.

    def __init__(self):
        self.questions = []

    def isEmpty(self):
        return True if len(self.questions) == 0 else False


# Interactions
# Interaction.json
# questionset.json
# question-type.json
class Content:

    data: dict

    def __init__(self, templateJSONFilePath: str):
        with open(templateJSONFilePath, "r") as file:
            self.data = json.loads(file.read())

    def addQuestion(self, question: Question):

        # Interaction thing depends on the time-stamp of the questions.

        self.data["interactiveVideo"]["assets"]["interactions"].append(jsonifiedQuestion)


class H5PMetaData:


# Take care of the json things and everything.
class H5P:

    # Take data and create json files and from templates and whatnot.
    def export(self):
        pass

    def jsonifyMCQuestion(self, mcQuestion):
        pass

    def jsonifySCQuestion(self, scQuestion):
        pass


def importVideos(inputVideoType, videosDirectoryPath):

    videoFileNames = glob.glob(
        os.path.join(
            videosDirectoryPath,
            "*." + inputVideoType
        )
    )
    videoFileNames.sort()
    videos = []
    for videoFileName in videoFileNames:
        video = VideoFileClip(videoFileName)
        videos.append(video)
    return videos


def combineVideos(videos, outputVideoFileName, outputsDirectoryPath):
    finalVideo = concatenate_videoclips(videos)
    outputVideoFilePath = os.path.join(
        outputsDirectoryPath,
        outputVideoFileName
    )
    finalVideo.write_videofile(outputVideoFilePath)
    return outputVideoFilePath

def createQuestionObject(answerChoices):

    # Go through the answer choices to organize answers and determine the type
    # of the question.
    numberOfCorrectAnswers = 0
    correctAnswersIndices = []
    for answerChoice in answerChoices:
        if answerChoice["isAnswer"]:
            numberOfCorrectAnswers += 1
            correctAnswersIndices.append(answerChoices.index(answerChoice))

    questionType = None
    questionObject = None
    # Creating question-object corresponding to the type.
    if numberOfCorrectAnswers == 1:
        questionType = "single"
        questionObject = []
        # Adding correction answer option at the beginning since that's how
        # h5p determines which option is the correct answer.
        correctAnswerChoiceIndex = correctAnswersIndices[0]
        correctAnswersIndices.pop()

        answerChoices = ["<p>{}</p>\n".format(answerChoice["choice"]) for answerChoice in answerChoices]

        correctAnswerChoice = answerChoices[correctAnswerChoiceIndex]
        answerChoices.pop(correctAnswerChoiceIndex)


        questionObject.append(correctAnswerChoice)
        questionObject += answerChoices

    elif numberOfCorrectAnswers > 1:
        questionType = "multiple"
        questionObject = []
        # Creating question-object corresponding to the type.
        # Fix this later by importing the format in.

        # Going through the questions in order and marking them and adding
        # the new question format.
        answerObjectTemplate = {
            "correct": False,
            "tipsAndFeedback": {
                "tip": "",
                "chosenFeedback": "",
                "notChosenFeedback": ""
            },
            "text": "<div>[REQ choice]</div>\n"
        }

        for answerChoice in answerChoices:
            answerObjectTemplateCopy = copy.deepcopy(answerObjectTemplate)
            if answerChoice["isAnswer"]:
                answerObjectTemplateCopy["correct"] = True
            answerObjectTemplateCopy["text"] = "<div>{}</div>\n".format(answerChoice["choice"]) # Really should rename this to "answer choice" or something.

            questionObject.append(answerObjectTemplateCopy)

    return questionType, questionObject

def createH5PContentJSON(videos, outputVideoFilePath, templatesDirectoryPath, questionsDirectoryPath, outputsDirectoryPath):

    singleChoiceTemplateFileName = "template_single_choice.json"
    singleChoiceTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        singleChoiceTemplateFileName
    )
    multipleChoicesTemplateFileName = "template_multiple_choices.json"
    multipleChoicesTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        multipleChoicesTemplateFileName
    )
    contentTemplateFileName = "template_content.json"
    contentTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        contentTemplateFileName
    )

    questionsFileName = "questions.txt"
    questionsFilePath = os.path.join(
        questionsDirectoryPath,
        questionsFileName
    )

    # Importing templates as dictionaries.
    with open(singleChoiceTemplateFilePath, "r") as templateFile:
        singleChoiceTemplate = json.loads(templateFile.read())
    with open(multipleChoicesTemplateFilePath, "r") as templateFile:
        multipleChoicesTemplate = json.loads(templateFile.read())
    with open(contentTemplateFilePath, "r") as templateFile:
        contentTemplate = json.loads(templateFile.read())


    # Creating content.json.
    with open(questionsFilePath, "r") as questionsFile:

        readingVideoSection = False
        videoTime = 0.0
        videoTimeStampForQuestions = 0.0
        questionArguments = {}

        while True:
            lastPosition = questionsFile.tell()
            line = questionsFile.readline()
            # Check if eof.
            if not line:
                break

            # Read contents of the video-section, which includes video file,
            # corresponding questions, etc.
            line = line.replace("\n", "")
            if readingVideoSection:
                # Video section ended.
                if "video:" in line:
                    questionsFile.seek(lastPosition)
                    readingVideoSection = False

                # Storing arguments for a given question.
                elif "@" in line:
                    argumentObject = line.replace("@", "").replace(" ","").split("=")
                    argumentType = argumentObject[0]
                    argument = argumentObject[1]

                    # Storing only time argument for now.
                    if argumentType == "gap":
                        questionArguments[argumentType] = argument


                # Checking if it's a question.
                elif re.search("(\d+\.)", line):
                    questionNumberToRemove = re.search("(\d+\.)", line).group(0)
                    questionTitle = line.replace(questionNumberToRemove, "").strip()

                    # Going through the question choices.
                    answerChoices = []
                    isEndOfFile = False
                    while True:
                        lastPosition = questionsFile.tell()
                        potentialQuestionChoice = questionsFile.readline()
                        # Check if eof.
                        if not potentialQuestionChoice:
                            break
                        potentialQuestionChoice = potentialQuestionChoice.replace("\n", "")


                        # Saving choices.
                        if re.search("([\[ \S]+[\]\)])", potentialQuestionChoice):
                            # Marked "choice": some-value and "isAnswer": Boolean
                            answerChoice = {}

                            # Marking them if they're the correct answer.
                            answerChoice["isAnswer"] = True if re.search(
                                "(\*.*[\]\)])",
                                potentialQuestionChoice
                            ) else False

                            # Removing the from component of the answer choice.
                            answerChoiceOptionValueToRemove = re.search(
                                "([\[ \S]+[\]\)])",
                                potentialQuestionChoice
                            ).group(0)

                            answerChoice["choice"] = potentialQuestionChoice.replace(
                                answerChoiceOptionValueToRemove,
                                ""
                            ).strip()

                            answerChoices.append(answerChoice)
                            continue

                        processQuestion = False
                        # Resetting when new video is found.
                        if "video:" in potentialQuestionChoice:
                            processQuestion = True
                            questionsFile.seek(lastPosition)
                            readingVideoSection = False
                        # Resetting when new question is found.
                        elif re.search("(\d+\.)", potentialQuestionChoice):
                            processQuestion = True
                            questionsFile.seek(lastPosition)
                        elif potentialQuestionChoice is None:
                            break

                        # Processing question components and adding them to the
                        # content template.
                        if processQuestion:

                            questionType, questionObject = createQuestionObject(
                                answerChoices=answerChoices
                            )

                            questionTemplateCopy = None
                            if questionType == "single":

                                questionTemplateCopy = copy.deepcopy(
                                    singleChoiceTemplate
                                )

                                # Adding starting time.
                                questionTemplateCopy["duration"][
                                    "from"] = videoTimeStampForQuestions

                                # Adding end time.
                                videoTimeStampForQuestions += 0.1
                                if "time" in questionArguments:
                                    videoTimeStampForQuestions += float(questionArguments["time"])
                                questionTemplateCopy["duration"][
                                    "to"] = videoTimeStampForQuestions

                                # Adding Question title.
                                questionTemplateCopy["action"]["params"][
                                    "choices"][0]["question"] = questionTitle
                                questionTemplateCopy["action"]["params"][
                                    "question"] = questionTitle
                                questionTemplateCopy[
                                    "label"] = questionTitle

                                # Adding question.
                                questionTemplateCopy["action"]["params"]["choices"][0]["answers"] = questionObject

                            elif questionType == "multiple":

                                questionTemplateCopy = copy.deepcopy(
                                    multipleChoicesTemplate
                                )

                                # Adding starting time.
                                questionTemplateCopy["duration"][
                                    "from"] = videoTimeStampForQuestions

                                # Adding end time.
                                videoTimeStampForQuestions += 0.1
                                if "time" in questionArguments:
                                    videoTimeStampForQuestions += float(questionArguments["time"])
                                questionTemplateCopy["duration"][
                                    "to"] = videoTimeStampForQuestions

                                # Adding Question title.
                                questionTemplateCopy["action"]["params"][
                                    "question"] = questionTitle
                                questionTemplateCopy[
                                    "label"] = questionTitle

                                # Adding question.
                                questionTemplateCopy["action"]["params"]["answers"] = questionObject

                            else:
                                print(questionType)
                                exit("This question type isn't supported.")
                            break
                    # Adding question object.
                    contentTemplate["interactiveVideo"]["assets"]["interactions"].append(questionTemplateCopy)
                    questionArguments = {}

            elif "video:" in line:
                videoFileName = line.replace("video:", "").strip()
                firstVideoFileName = videos[0].filename.split("/")[-1]
                # Checking to make sure the video we're dealing with is the
                # correct one.
                if firstVideoFileName == videoFileName:
                    videoTime += videos[0].duration
                    videoTimeStampForQuestions = videoTime
                    videos.pop(0)
                readingVideoSection = True
    #
    # {interactiveVideo
    # video
    # files(path
    # mime)

    contentTemplate["interactiveVideo"]["video"]["files"][0]["path"] = outputVideoFilePath
    contentTemplate["interactiveVideo"]["video"]["files"][0]["mime"] = "video/mp4"
    # Add video path.

    # Creating new question-dictionaries and creating content object for every
    # video
    outputJSONObject = json.dumps(contentTemplate)
    with open(os.path.join(outputsDirectoryPath, "content.json"), "w") as outputJSONFile:
        outputJSONFile.write(outputJSONObject)


def main():

    # Creating system paths based on the local OS.
    workingDirectory = os.getcwd()

    useTestData = False
    if useTestData:
        inputsDirectory = "test_inputs/"
    else:
        inputsDirectory = "inputs/"

    videosDirectory = "videos/"
    inputVideoType = "mov"
    videosDirectoryPath = os.path.join(
        workingDirectory,
        inputsDirectory,
        videosDirectory
    )

    templatesDirectory = "templates/"
    templatesDirectoryPath = os.path.join(
        workingDirectory,
        templatesDirectory
    )

    outputsDirectory = "h5p/content/"
    outputVideoName = "final_h5p_video.mp4"  # Only mp4 is supported for now.
    outputsDirectoryPath = os.path.join(
        workingDirectory,
        outputsDirectory
    )

    questionsDirectory = "questions"
    questionsDirectoryPath = os.path.join(
        workingDirectory,
        inputsDirectory,
        questionsDirectory
    )

    # Creating h5p directory
    h5pTemplateDirectory = "template_h5p_package_multiple_choice/"
    source = os.path.join(templatesDirectoryPath, h5pTemplateDirectory)
    destination = os.path.join(workingDirectory, "h5p/")
    shutil.copytree(source, destination)

    # Import videos
    videos = importVideos(
        inputVideoType=inputVideoType,
        videosDirectoryPath=videosDirectoryPath
    )

    # Combine videos in to a single video.
    outputVideoFilePath = combineVideos(
        videos=videos,
        outputVideoFileName=outputVideoName,
        outputsDirectoryPath=outputsDirectoryPath
    )

    # Create folders if they don't exist.
    # Create content.json and h5p.json.
    createH5PContentJSON(
        videos=videos,
        outputVideoFilePath=outputVideoFilePath,
        templatesDirectoryPath=templatesDirectoryPath,
        questionsDirectoryPath=questionsDirectoryPath,
        outputsDirectoryPath=outputsDirectoryPath
    )

    # Create h5p.json.


    # Zip h5p directory


if __name__ == "__main__":
    main()
