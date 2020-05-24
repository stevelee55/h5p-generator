import os
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


def createContentJSON(videos):

    # Import template JSON file.
    with open("./templates/template_content.json", "r") as templateJSONFile, open("./contents/outputs/content.json", "w+") as outputJSONFile:
        for line in templateJSONFile:
            outputJSONFile.write(line)

        templateJSONFile.close()
        outputJSONFile.close()

    return



def main():

    # Import videos
    videosDirectoryPath = "./test_contents/videos"
    videoFileType = "mov"
    videos = importVideos(
        videosDirectoryPath,
        videoFileType
    )

    # Combine videos in to a single video.
    outputDirectoryPath = "./test_contents/outputs"
    outputVideoFileName = "final_h5p_video.mp4" # Only mp4 is supported for now.
    combineVideos(
        videos,
        outputDirectoryPath,
        outputVideoFileName
    )

    # Create folders if they don't exist.

    # Create content.json and h5p.json.
    contentJSON = createContentJSON(videos)


if __name__ == "__main__":
    main()
