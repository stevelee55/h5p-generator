import os
import json
import copy
import re
import glob
from moviepy.editor import VideoFileClip, concatenate_videoclips


def importVideos(videoFileType, videosDirectoryPath):

    videoFileNames = glob.glob(
        os.path.join(
            videosDirectoryPath,
            "*." + videoFileType
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
    finalVideo.write_videofile(
        os.path.join(
            outputsDirectoryPath,
            outputVideoFileName
        )
    )


def createH5P(videos, templatesDirectoryPath, questionsDirectoryPath, outputsDirectoryPath):

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

                # Checking if it's a question.
                elif re.search("(\d+\.)", line):
                    questionNumberToRemove = re.search("(\d+\.)", line).group(0)
                    questionTitle = line.replace(questionNumberToRemove, "").strip()

                    singleChoiceTemplateCopy = copy.deepcopy(singleChoiceTemplate)

                    # Adding starting time.
                    singleChoiceTemplateCopy["duration"]["from"] = videoTimeStampForQuestions

                    # Adding end time: Questions have 3 seconds.
                    videoTimeStampForQuestions += 3
                    singleChoiceTemplateCopy["duration"]["to"] = videoTimeStampForQuestions

                    # Adding Questions and answers.
                    singleChoiceTemplateCopy["action"]["params"]["choices"][0]["question"] = questionTitle
                    singleChoiceTemplateCopy["action"]["params"]["question"] = questionTitle
                    singleChoiceTemplateCopy["label"] = questionTitle


                # something weird here - fix it.
                    # has to do with how the questions answers options are being added.

                    # Going through the question choices.
                    while True:
                        lastPosition = questionsFile.tell()
                        potentialQuestion = questionsFile.readline()
                        # Go one line backwards if next question is found.
                        if re.search("(\S+\))", potentialQuestion):
                            questionsFile.seek(lastPosition)
                            break
                        elif "video:" in line:
                            questionsFile.seek(lastPosition)
                            readingVideoSection = False
                            break
                        elif "*" in potentialQuestion:
                            potentialQuestion = potentialQuestion.replace("* ", "")
                            singleChoiceTemplateCopy["action"]["params"]["choices"][0]["answers"].append("<p>%s</p>\n" % potentialQuestion)

                    # Adding question object.
                    contentTemplate["interactiveVideo"]["assets"]["interactions"].append(singleChoiceTemplateCopy)

            elif "video:" in line:
                videoFileName = line.replace("video:", "").strip()
                firstVideoFileName = videos[0].filename.split("/")[len(videos[0].filename)-1]
                # Checking to make sure the video we're dealing with is the
                # correct one.
                if firstVideoFileName == videoFileName:
                    videoTime += videos[0].duration
                    videoTimeStampForQuestions = videoTime
                    videos.pop(0)
                readingVideoSection = True


    # Creating new question-dictionaries and creating content object for every
    # video
    outputJSONObject = json.dumps(contentTemplate)
    with open("./contents/outputs/workspace/content/content.json", "w") as outputJSONFile:
        outputJSONFile.write(outputJSONObject)
    return



def main():

    workingDirectory = "./"

    useTestData = False
    if useTestData:
        inputsDirectory = "inputs/"
    else:
        inputsDirectory = "test_inputs/"

    videosDirectory = "videos/"
    inputVideoType = "mov"
    videosDirectoryPath = os.path.join(
        workingDirectory,
        inputsDirectory,
        videosDirectory
    )

    outputsDirectory = "outputs/"
    outputVideoName = "final_h5p_video.mp4"  # Only mp4 is supported for now.
    outputsDirectoryPath = os.path.join(
        workingDirectory,
        outputsDirectory
    )

    templatesDirectory = "templates/"
    templatesDirectoryPath = os.path.join(
        workingDirectory,
        templatesDirectory
    )

    questionsDirectory = "questions"
    questionsDirectoryPath = os.path.join(
        workingDirectory,
        inputsDirectory,
        questionsDirectory
    )

    # Import videos
    videos = importVideos(
        inputVideoType=inputVideoType,
        videosDirectoryPath=videosDirectoryPath
    )

    # Combine videos in to a single video.
    combineVideos(
        videos=videos,
        outputVideoFileName=outputVideoName,
        outputsDirectoryPath=outputsDirectoryPath
    )

    # Create folders if they don't exist.
    # Create content.json and h5p.json.
    createH5P(
        videos=videos,
        templatesDirectoryPath=templatesDirectoryPath,
        questionsDirectoryPath=questionsDirectoryPath,
        outputsDirectoryPath=outputsDirectoryPath
    )


if __name__ == "__main__":
    main()
