class VideoStream:
    def __init__(self, filename):
        self.filename = '/home/core/Desktop/ESR/fase2/st1/' + filename
        print(self.filename)
        try:
            self.file = open(self.filename, 'rb')
        except Exception:
            raise IOError
        self.frameNum = 0

    def nextFrame(self):
        """ Get next frame"""
        data = self.file.read(5)  # Get the framelength from the first 5 bits
        if data:
            try:
                framelength = int(data)
                # Read the current frame
                data = self.file.read(framelength)
                self.frameNum += 1
            except ValueError as ve:
                print(ve)
                
        return data

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum