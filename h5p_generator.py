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
    _templatePath: str

    def __init__(self, question: str, choices: list, templatePath: str):
        self.question = question
        self.choices = choices
        self.questionType = QuestionType.SINGLE_CHOICE
        self._templatePath = templatePath

    @staticmethod
    def _convertChoicesToList(question: str, choices: list):
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
        with open(self._templatePath, "r") as templateFile:
            template = json.loads(templateFile.read())
            template["params"]["question"] = "<p>{}</p>\n".format(
                self.question)
            # Getting rid of default contents by replacing the whole thing.
            # Also need to pass in the "question" because of the formatting
            # of the template.
            template["params"]["choices"] = self._convertChoicesToList(
                self.question,
                self.choices
            )
            return template


class MultipleChoicesQuestion(Question):
    questionType: QuestionType
    _templatePath: str

    def __init__(self, question: str, choices: list, templatePath: str):
        self.question = question
        self.choices = choices
        self.questionType = QuestionType.MULTIPLE_CHOICES
        self._templatePath = templatePath

    @staticmethod
    def _convertChoiceToDict(choice: Choice):
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
        with open(self._templatePath, "r") as templateFile:
            template = json.loads(templateFile.read())
            for choice in self.choices:
                template["params"]["answers"].append(
                    self._convertChoiceToDict(choice)
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

    def __init__(self, templatePath: str, questions: list = None,
                 startTime: float = 0.0, endTime: float = 0.0):
        self.questions = questions if questions else []
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
    def convertQuestionSetToInteraction(questionSet: QuestionSet,
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
            content["interactiveVideo"]["video"]["files"][0]["path"] = videoSource # Wrong. Needs to be relative.
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


def importVideos(inputVideoType,
                 videosDirectoryPath
                 ):
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


def combineVideos(videos,
                  outputVideoFileName,
                  outputsDirectoryPath
                  ):
    finalVideo = concatenate_videoclips(videos)
    outputVideoFilePath = os.path.join(
        outputsDirectoryPath,
        outputVideoFileName
    )
    finalVideo.write_videofile(outputVideoFilePath)
    return outputVideoFilePath


def determineQuestionTypeFrom(answerChoices: list):
    numberOfCorrectAnswers = 0
    for answerChoice in answerChoices:
        if answerChoice.isCorrect():
            numberOfCorrectAnswers += 1
            if numberOfCorrectAnswers > 1:
                break
    return QuestionType.SINGLE_CHOICE if numberOfCorrectAnswers == 1 else QuestionType.MULTIPLE_CHOICES


def createQuestionSetsFrom(videos: list,
                           outputVideoFilePath: str,
                           templatesDirectoryPath: str,
                           questionsDirectoryPath: str,
                           outputsDirectoryPath: str
                           ):
    # Go through the questions from the questions.txt and create a list of
    # QuestionSets.

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
    questionSetTemplateFileName = "template_question_set.json"
    questionSetTemplateFilePath = os.path.join(
        templatesDirectoryPath,
        questionSetTemplateFileName
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

    # Importing templates as dictionaries. May not need this.
    with open(singleChoiceTemplateFilePath, "r") as templateFile:
        singleChoiceTemplate = json.loads(templateFile.read())
    with open(multipleChoicesTemplateFilePath, "r") as templateFile:
        multipleChoicesTemplate = json.loads(templateFile.read())
    with open(contentTemplateFilePath, "r") as templateFile:
        contentTemplate = json.loads(templateFile.read())

    # Creating QuestionSets.
    with open(questionsFilePath, "r") as questionsFile:
        collectingQuestions = False
        videoTime = 0.0
        questionSet = None
        questionSets = []
        while True:
            # For each line
            # If Line is video, start collecting stuff in a data structure.
                # If the line doesn't start with video, file error.
            # As the questions are being collected, if a new video line appears,
            # save the current questions and the video and continue with the
            # new video and questions.
            # Stop collecting when there are no more questions.

            # submit questions when it's either video or end of file.

            line = questionsFile.readline()
            if line:
                line = line.replace("\n", "")
            else:
                # FIX ME: It's not clean. Duplicate code.
                # Add the previous question set to the list if there was one.
                if questionSet:
                    questionSet.startTime = videoTime
                    # This value should be a constant.
                    videoTime += 2
                    questionSet.endTime = videoTime
                    questionSets.append(questionSet)
                break
            if "video:" in line:
                # Add the previous question set to the list if there was one.
                if questionSet:
                    questionSet.startTime = videoTime
                    # This value should be a constant.
                    videoTime += 2
                    questionSet.endTime = videoTime
                    questionSets.append(questionSet)
                videoFileName = line.replace("video:", "").strip()
                firstVideoFileName = videos[0].filename.split("/")[-1]
                # Checking to make sure the video we're dealing with is the
                # correct one.
                if firstVideoFileName == videoFileName:
                    videoTime += videos[0].duration
                    videos.pop(0)
                # Collecting questions for current video.
                questionSet = QuestionSet(
                    templatePath=questionSetTemplateFilePath
                )
                collectingQuestions = True
            elif collectingQuestions:
                # Checking if it's a question.
                if re.search("(\d+\.)", line):
                    # Getting question title.
                    questionNumberToRemove = re.search(
                        "(\d+\.)",
                        line
                    ).group(0)
                    questionTitle = line.replace(
                        questionNumberToRemove,
                        ""
                    ).strip()

                    # Going through the question choices.
                    answerChoices = []
                    while True:
                        lastPosition = questionsFile.tell()
                        potentialQuestionChoice = questionsFile.readline()
                        # Checking if the current line is valid for reading in
                        # choices or start creating new question and adding it
                        # to question set.
                        processQuestion = False
                        if potentialQuestionChoice:
                            potentialQuestionChoice = potentialQuestionChoice.replace(
                                "\n",
                                ""
                            )
                            # New video found.
                            if "video:" in potentialQuestionChoice:
                                questionsFile.seek(lastPosition)
                                collectingQuestions = False
                                processQuestion = True
                            # New question found.
                            elif re.search("(\d+\.)", potentialQuestionChoice):
                                questionsFile.seek(lastPosition)
                                processQuestion = True
                            elif potentialQuestionChoice == "":
                                continue
                        else:
                            # This is the last question to be processed.
                            processQuestion = True
                        # Saving choices if it's not time to process the
                        # question and the choices as a whole.
                        if not processQuestion:
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
                                answerChoices.append(
                                    Choice(
                                        choice=answerChoice["choice"],
                                        isCorrect=answerChoice["isAnswer"]
                                    )
                                )
                                continue
                        else:
                            questionType = determineQuestionTypeFrom(
                                answerChoices=answerChoices
                            )
                            if questionType == QuestionType.SINGLE_CHOICE:
                                singleChoiceQuestion = SingleChoiceQuestion(
                                    question=questionTitle,
                                    choices=answerChoices,
                                    templatePath=singleChoiceTemplateFilePath
                                )
                                questionSet.questions.append(singleChoiceQuestion)
                            elif questionType == QuestionType.MULTIPLE_CHOICES:
                                multipleChoicesQuestion = MultipleChoicesQuestion(
                                    question=questionTitle,
                                    choices=answerChoices,
                                    templatePath=multipleChoicesTemplateFilePath
                                )
                                questionSet.questions.append(
                                    multipleChoicesQuestion)
                            else:
                                print(questionType)
                                exit("This question type isn't supported.")
                            break
        return questionSets


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
    # Checking if the directory already exists.
    if os.path.isdir(destination):
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    # Import videos.
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

    content = Content(questionSets=questionSets)
    h5pTitle = "Raj Nadakuditi's Lecture"
    h5pMetaData = H5PMetaData(title=h5pTitle)
    h5p.export(content=content, h5pMetaData=h5pMetaData)

    # Zip h5p directory


if __name__ == "__main__":
    main()
