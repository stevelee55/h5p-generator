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

    # Create content.json and h5p.json.
    for video in videos:
        print(video.filename)
        print(video.duration)



if __name__ == "__main__":
    main()
