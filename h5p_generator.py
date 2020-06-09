import os
import json
import copy
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

    # Importing config file.
    with open(questionsFilePath, "r") as configFile:
        videoSectionReading = False
        videoTime = 0.0
        videoTimeStampForQuestions = 0.0
        while True:
            # Checking if the line exists.
            line = configFile.readline()
            if not line:
                break
            # Read contents of the video-section, which includes video file,
            # corresponding questions, etc.
            line = line.replace("\n", "")
            if videoSectionReading:
                if "video:" in line:
                    videoFileName = line.replace("video: ", "") # Make it less space-dependent.
                    if videos[0].filename.replace("./contents/videos/", "") == videoFileName:
                        videoTime += videos[0].duration
                        videoTimeStampForQuestions = videoTime
                        videos.pop(0)

                elif "question:" in line:
                    questionTitle = line.replace("question: ", "") # Make it less space-dependent.

                    print(questionTitle)

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

                    # Going through the question choices.
                    while True:
                        lastPosition = configFile.tell()
                        potentialQuestion = configFile.readline()
                        if "question:" in potentialQuestion:
                            # Go one backwards if next question is found.
                            configFile.seek(lastPosition)
                            break
                        elif "}" in potentialQuestion:
                            videoSectionReading = False
                            break
                        elif "*" in potentialQuestion:
                            potentialQuestion = potentialQuestion.replace("* ", "")
                            singleChoiceTemplateCopy["action"]["params"]["choices"][0]["answers"].append("<p>%s</p>\n" % potentialQuestion)

                    # Adding question object.
                    contentTemplate["interactiveVideo"]["assets"]["interactions"].append(singleChoiceTemplateCopy)

                elif "}" in line:
                    videoSectionReading = False

            elif "{" in line:
                videoSectionReading = True


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
