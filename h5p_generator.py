import moviepy

# Input: Directory path where the videos are at.
# Output: Create and return video objects.
def importVideos(directoryPath):

    pass


# The issues that might come up would be the memory issue if the videos
# are too large and to
def combineVideos(videos):
    pass


def main():

    from moviepy.editor import VideoFileClip, concatenate_videoclips
    clip1 = VideoFileClip("./tests/original.mov")
    print(clip1.duration)
    # clip2 = VideoFileClip("./tests/processed.mov").subclip(3, 7)
    # final_clip = concatenate_videoclips([clip1, clip2])
    # final_clip.write_videofile("./tests/my_concatenation.mp4")

    # Import videos
    directoryPath = "./tests"
    videos = importVideos(directoryPath)

    # Combine videos in to a single video.
    combinedVideo = combineVideos(videos)

    # Create content.json and h5p.json.




if __name__ == "__main__":
    main()
