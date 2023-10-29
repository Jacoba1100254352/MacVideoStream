# For Mac
import numpy as np
import cv2, io, socket, struct, time, CoreMedia
from Quartz import CoreVideo

IMG_W = 1280
IMG_H = 720

server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8000))
server_socket.listen(0)

connection = server_socket.accept()[0].makefile('rb')

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_W)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_H)

try:
    display_link = CoreVideo.CVDisplayLinkCreateWithActiveCGDisplays(None)
    while True:
        ret, frame = cam.read()
        flipped = cv2.flip(frame, 1)
        if frame is not None:
            print("frame is not None, proceed with flip")
            flipped = cv2.flip(frame, 1)
            frame[0: IMG_H, IMG_W // 2: IMG_W] = flipped[0: IMG_H, IMG_W // 2: IMG_W]
        else:
            print("frame is None, skipping flip")
        # Read the length of the image as a 32-bit unsigned int.
        image_len_packed = connection.read(struct.calcsize('<L'))
        if not image_len_packed:
            break
        image_len = struct.unpack('<L', image_len_packed)[0]
        # Read the image data.
        image_stream = io.BytesIO()
        remaining = image_len
        while remaining > 0:
            chunk = connection.read(min(remaining, 4096))
            if not chunk:
                break
            image_stream.write(chunk)
            remaining -= len(chunk)
        # Rewind the stream
        image_stream.seek(0)

        image = np.array(bytearray(image_stream.read()), dtype=np.uint8)
        frame = cv2.imdecode(image, cv2.IMREAD_COLOR)
        # Resize the frame to the desired size for the virtual camera
        if frame is not None and frame.shape == (IMG_H, IMG_W, 3):
            print("frame is not None and has correct shape")
            frame = cv2.resize(frame, (IMG_W, IMG_H))
        else:
            print("frame is None or has incorrect shape, skipping resize")
        # Convert the frame to a format suitable for OS X's AVFoundation framework
        if frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
            print("frame is not None and has dimensions")
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        else:
            print("frame is None or has no dimensions, skipping cvtColor")

        # Create a `CVPixelBuffer` from the image data
        if frame is not None:
            print("frame and pixel_buffer are not none")
            pixel_buffer = CoreVideo.CVPixelBufferCreateWithBytes(
                IMG_W, IMG_H, CoreVideo.kCVPixelFormatType_32BGRA,
                frame.tobytes(), frame.strides[0],
                None, None, None, None, None,
            )

            # Create a `CMSampleBuffer` from the pixel buffer
            sample_buffer = CoreMedia.CMSampleBufferCreateForImageBuffer(
                None, pixel_buffer, True, None, None,
                CoreMedia.kCMSampleAttachmentKey_DisplayImmediately,
            )

            # Send the sample buffer to the virtual camera
            CoreVideo.CVDisplayLinkStart(display_link)
            CoreVideo.CVPixelBufferLockBaseAddress(pixel_buffer, 0)
            CoreVideo.CVDisplayLinkRender(display_link, sample_buffer)
            CoreVideo.CVPixelBufferUnlockBaseAddress(pixel_buffer, 0)
            CoreVideo.CVDisplayLinkStop(display_link)
        else:
            print("frame is None, skipping")

except Exception as e:
    print(e)

finally:
    cam.release()
    CoreVideo.CVDisplayLinkStop(display_link)
    CoreVideo.CVDisplayLinkRelease(display_link)
