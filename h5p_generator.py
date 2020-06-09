import os
import json
import copy
import glob
from moviepy.editor import VideoFileClip, concatenate_videoclips


# Input: Directory path where the videos are at.
# Output: Creates and returns video objects.
def importVideos(videosDirectoryPath, videoFileType):

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


def combineVideos(videos, outputDirectoryPath, outputVideoFileName):

    finalVideo = concatenate_videoclips(videos)
    finalVideo.write_videofile(
        os.path.join(
            outputDirectoryPath,
            outputVideoFileName
        )
    )


# Create content.json contents from templates, video durations, and config.txt
def createContentJSON(videos):

    # Importing templates as dictionaries.
    with open("./templates/template_single_choice.json", "r") as templateFile:
        singleChoiceTemplate = json.loads(templateFile.read())
    with open("./templates/template_multiple_choices.json", "r") as templateFile:
        multipleChoicesTemplate = json.loads(templateFile.read())
    with open("./templates/template_content.json", "r") as templateFile:
        contentTemplate = json.loads(templateFile.read())

    # Importing config file.
    with open("./contents/config.txt", "r") as configFile:
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

    useTestData = False
    if useTestData:
        inputsDirectory = "inputs/"
    else:
        inputsDirectory = "test_inputs/"

    workingDirectory = "./"
    videosDirectory = "videos/"
    outputsDirectory = "outputs/"
    inputVideoType = "mov"
    outputVideoName = "final_h5p_video.mp4"  # Only mp4 is supported for now.

    videosDirectoryPath = os.path.join(
        workingDirectory,
        inputsDirectory,
        videosDirectory
    )

    outputDirectoryPath = os.path.join(
        workingDirectory,
        outputsDirectory
    )

    # Import videos
    videos = importVideos(
        videosDirectoryPath=videosDirectoryPath,
        inputVideoType=inputVideoType
    )

    # Combine videos in to a single video.
    combineVideos(
        videos=videos,
        outputDirectoryPath=outputDirectoryPath,
        outputVideoFileName=outputVideoName
    )

    # Create folders if they don't exist.
    # Create content.json and h5p.json.
    contentJSON = createContentJSON(videos)


if __name__ == "__main__":
    main()
