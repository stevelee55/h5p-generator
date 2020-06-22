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


class Choice:
    text: str
    type: bool

    def __init__(self, choice: str, isCorrect: bool):
        self.text = choice
        self.type = isCorrect

    def isCorrect(self):
        return True if self.type else False


class Question:
    question: str
    choices: list

    def __init__(self, question: str, choices: list):
        self.question = question
        self.choices = choices


class SingleChoiceQuestion(Question):
    questionType: QuestionType
    templatePath: str

    def __init__(self, question: str, choices: list, templatePath: str):
        self.question = question
        self.choices = choices
        self.questionType = QuestionType.SINGLE_CHOICE
        self.templatePath = templatePath

    @staticmethod
    def convertChoicesToList(question: str, choices: list):
        formattedChoicesList = []
        mainTemplate = {
            "subContentId": "",
            "question": "<p><question-title></p>\n",
            "answers": [
                "<p><first-one-is-answer></p>\n",
                "<p><other-choice></p>\n",
                "<p><another-choice></p>\n"
            ]
        }
        metaData = {
            "subContentId": ""
        }

        mainTemplate["question"] = question

        # Rearranging choices so the answer choice is the first element.
        for choice in choices:
            if choice.isCorrect():
                # Taking the correction choice and moving it to the index 0
                # of the choices list.
                choices.insert(0, choices.pop(choices.index(choice)))
                break

        # Creating a list of choices in template format.
        formattedChoices = []
        for choice in choices:
            choiceTemplate = "<p>{}</p>\n"
            formattedChoices.append(choiceTemplate.format(choice.text))

        mainTemplate["answers"] = formattedChoices

        formattedChoicesList.append(mainTemplate)
        formattedChoicesList.append(metaData)

        return formattedChoicesList

    def convertToDict(self):
        with open(self.templatePath, "r") as templateFile:
            template = json.loads(templateFile.read())
            template["params"]["question"] = "<p>{}</p>\n".format(
                self.question)
            # Getting rid of default contents by replacing the whole thing.
            # Also need to pass in the "question" because of the formatting
            # of the template.
            template["params"]["choices"] = self.convertChoicesToList(
                self.question,
                self.choices
            )
            return template


class MultipleChoicesQuestion(Question):
    questionType: QuestionType
    templatePath: str

    def __init__(self, question: str, choices: list):
        self.question = question
        self.choices = choices
        self.questionType = QuestionType.MULTIPLE_CHOICES

    @staticmethod
    def convertChoiceToDict(choice: Choice):
        template = {
            "text": "<div><correct-answer-choice></div>\n",
            "correct": False,
            "tipsAndFeedback": {
                "tip": "",
                "chosenFeedback": "",
                "notChosenFeedback": ""
            }
        }
        template["text"] = choice.text
        template["correct"] = choice.type

        return template

    def convertToDict(self):
        with open(self.templatePath, "r") as templateFile:
            template = json.loads(templateFile.read())

            for choice in self.choices:
                template["params"]["answers"].append(
                    self.convertChoiceToDict(choice)
                )

            return template


class QuestionSet:
    """
    Question set per video.
    """

    questions: list
    startTime: float
    endTime: float
    templatePath: str

    def __init__(self, questions: list, startTime: float, endTime: float,
                 templatePath: str):
        self.questions = questions
        self.startTime = startTime
        self.endTime = endTime
        self.templatePath = templatePath

    def convertToDict(self):
        with open(self.templatePath, "r") as templateFile:
            template = json.loads(templateFile.read())

            for question in self.questions:
                template["params"]["questions"].append(
                    question.convertToDict())

            return template


# textqti parser creates questionsets and passes them to content.
class Content:
    # Add more to customize more field, but for now, only do questions.
    questionSets: list

    def __init__(self, questionSets: list):
        self.questionSets = questionSets

    @staticmethod
    def convertQuestionToInteraction(questionSet: QuestionSet,
                                     interactionTemplatePath: str):
        with open(interactionTemplatePath, "r") as templateFile:
            interaction = json.loads(templateFile.read())
            interaction["action"] = questionSet.convertToDict()
            interaction["duration"]["from"] = questionSet.startTime
            interaction["duration"]["to"] = questionSet.endTime
            return interaction

    def export(self, outputFileName: str, contentTemplatePath: str, interactionTemplatePath: str,
               outputsDirectoryPath: str, videoSource: str):
        outputFilePath = os.path.join(outputsDirectoryPath, outputFileName)
        with open(contentTemplatePath, "r") as templateFile, open(
                outputFilePath, "w") as outputFile:
            content = json.loads(templateFile.read())
            for questionSet in self.questionSets:
                content["interactiveVideo"]["assets"]["interactions"].append(
                    self.convertQuestionSetToInteraction(
                        questionSet=questionSet,
                        interactionTemplatePath=interactionTemplatePath
                    )
                )
            # Setting video source.
            content["interactiveVideo"]["video"]["files"][0]["path"] = videoSource
            mime = "video/mp4" if ".mp4" in videoSource else "video/YouTube"
            content["interactiveVideo"]["video"]["files"][0]["mime"] = mime

            outputFile.write(json.dumps(content))


class H5PMetaData:
    title: str

    def __init__(self, title: str):
        self.title = title

    def export(self, outputFileName: str, h5pMetaDataTemplatePath: str, outputsDirectoryPath: str):
        outputFilePath = os.path.join(outputsDirectoryPath, outputFileName)
        with open(h5pMetaDataTemplatePath, "r") as templateFile, open(
                outputFilePath, "w") as outputFile:
            h5pMetaData = json.loads(templateFile.read())
            h5pMetaData["title"] = self.title
            outputFile.write(json.dumps(h5pMetaData))


# Take care of the json things and everything.
class H5P:
    contentTemplatePath: str
    interactionTemplatePath: str
    h5pMetaDataTemplatePath: str
    outputsDirectoryPath: str
    videoSource: str

    def __init__(self, contentTemplatePath: str, interactionTemplatePath: str,
                 h5pMetaDataTemplatePath: str, outputsDirectoryPath: str,
                 videoSource: str):
        self.contentTemplatePath = contentTemplatePath
        self.interactionTemplatePath = interactionTemplatePath
        self.h5pMetaDataTemplatePath = h5pMetaDataTemplatePath
        self.outputsDirectoryPath = outputsDirectoryPath
        self.videoSource = videoSource

    # Take data and create json files and from templates and whatnot.
    def export(self, content: Content, h5pMetaData: H5PMetaData):
        content.export(
            outputFileName="content.json",
            contentTemplatePath=self.contentTemplatePath,
            interactionTemplatePath=self.interactionTemplatePath,
            outputsDirectoryPath=self.outputsDirectoryPath,
            videoSource=self.videoSource
        )
        h5pMetaData.export(
            outputFileName="h5p.json",
            h5pMetaDataTemplatePath=self.h5pMetaDataTemplatePath,
            outputsDirectoryPath=self.outputsDirectoryPath
        )


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

        answerChoices = ["<p>{}</p>\n".format(answerChoice["choice"]) for
                         answerChoice in answerChoices]

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
            answerObjectTemplateCopy["text"] = "<div>{}</div>\n".format(
                answerChoice[
                    "choice"])  # Really should rename this to "answer choice" or something.

            questionObject.append(answerObjectTemplateCopy)

    return questionType, questionObject


def createH5PContentJSON(videos, templatesDirectoryPath, questionsDirectoryPath):
    singleChoiceTemplateFileName = "template_question_single_choice.json"
    singleChoiceTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        singleChoiceTemplateFileName
    )
    multipleChoicesTemplateFileName = "template_question_multiple_choices.json"
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
                    argumentObject = line.replace("@", "").replace(" ",
                                                                   "").split(
                        "=")
                    argumentType = argumentObject[0]
                    argument = argumentObject[1]

                    # Storing only time argument for now.
                    if argumentType == "gap":
                        questionArguments[argumentType] = argument


                # Checking if it's a question.
                elif re.search("(\d+\.)", line):
                    questionNumberToRemove = re.search("(\d+\.)", line).group(
                        0)
                    questionTitle = line.replace(questionNumberToRemove,
                                                 "").strip()

                    # Going through the question choices.
                    answerChoices = []
                    isEndOfFile = False
                    while True:
                        lastPosition = questionsFile.tell()
                        potentialQuestionChoice = questionsFile.readline()
                        # Check if eof.
                        if not potentialQuestionChoice:
                            break
                        potentialQuestionChoice = potentialQuestionChoice.replace(
                            "\n", "")

                        # Saving choices.
                        if re.search("([\[ \S]+[\]\)])",
                                     potentialQuestionChoice):
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

                            answerChoice[
                                "choice"] = potentialQuestionChoice.replace(
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
                                    videoTimeStampForQuestions += float(
                                        questionArguments["time"])
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
                                questionTemplateCopy["action"]["params"][
                                    "choices"][0]["answers"] = questionObject

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
                                    videoTimeStampForQuestions += float(
                                        questionArguments["time"])
                                questionTemplateCopy["duration"][
                                    "to"] = videoTimeStampForQuestions

                                # Adding Question title.
                                questionTemplateCopy["action"]["params"][
                                    "question"] = questionTitle
                                questionTemplateCopy[
                                    "label"] = questionTitle

                                # Adding question.
                                questionTemplateCopy["action"]["params"][
                                    "answers"] = questionObject

                            else:
                                print(questionType)
                                exit("This question type isn't supported.")
                            break
                    # Adding question object.
                    contentTemplate["interactiveVideo"]["assets"][
                        "interactions"].append(questionTemplateCopy)
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




def main():
    # Directories.
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

    # Templates.
    interactionTemplateFileName = "template_interaction.json"
    interactionTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        interactionTemplateFileName
    )

    contentTemplateFileName = "template_content.json"
    contentTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        contentTemplateFileName
    )

    h5pMetaDataTemplateFileName = "template_h5p.json"
    h5pMetaDataTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        h5pMetaDataTemplateFileName
    )

    # Creating h5p directory.
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

    h5p = H5P(contentTemplatePath=contentTemplateFilePath,
              interactionTemplatePath=interactionTemplateFilePath,
              h5pMetaDataTemplatePath=h5pMetaDataTemplateFilePath,
              outputsDirectoryPath=outputsDirectoryPath,
              videoSource=outputVideoFilePath)

    # Create folders if they don't exist.
    # Create content.json and h5p.json.
    questionSets = createQuestionSetsFrom(
        videos=videos,
        outputVideoFilePath=outputVideoFilePath,
        templatesDirectoryPath=templatesDirectoryPath,
        questionsDirectoryPath=questionsDirectoryPath,
        outputsDirectoryPath=outputsDirectoryPath
    )

    h5pTitle = "Raj Nadakuditi's Lecture"
    h5pMetaData = H5PMetaData(title=h5pTitle)
    content = Content(questionSets=questionSets)
    h5p.export(content=content, h5pMetaData=h5pMetaData)

    # Zip h5p directory


if __name__ == "__main__":
    main()
