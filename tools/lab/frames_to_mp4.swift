// Pictures to a video, with what macOS brings along (no download needed).
//
//   swift tools/lab/frames_to_mp4.swift <folder with .png pictures> <out.mp4> <pictures a second> <bits a second>
//
// The pictures are taken in the order of their names; all of one size.
// tools/post_clip.py calls this.
import AVFoundation
import CoreGraphics
import Foundation
import ImageIO

let args = CommandLine.arguments
guard args.count >= 5, let fps = Int32(args[3]), let bits = Int(args[4]) else {
  print("usage: frames_to_mp4 <folder> <out.mp4> <pictures a second> <bits a second>")
  exit(1)
}
let folder = URL(fileURLWithPath: args[1])
let out = URL(fileURLWithPath: args[2])

func load(_ name: String) -> CGImage? {
  guard let src = CGImageSourceCreateWithURL(folder.appendingPathComponent(name) as CFURL, nil) else { return nil }
  return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

let names = ((try? FileManager.default.contentsOfDirectory(atPath: folder.path)) ?? [])
  .filter { $0.hasSuffix(".png") }.sorted()
guard let first = names.first.flatMap(load) else {
  print("no pictures in \(folder.path)")
  exit(1)
}
let w = first.width, h = first.height

try? FileManager.default.removeItem(at: out)
guard let writer = try? AVAssetWriter(outputURL: out, fileType: .mp4) else {
  print("cannot write \(out.path)")
  exit(1)
}
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
  AVVideoCodecKey: AVVideoCodecType.h264,
  AVVideoWidthKey: w,
  AVVideoHeightKey: h,
  AVVideoCompressionPropertiesKey: [
    AVVideoAverageBitRateKey: bits,
    AVVideoMaxKeyFrameIntervalKey: Int(fps) * 3,
    AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
    AVVideoExpectedSourceFrameRateKey: Int(fps),
    AVVideoAllowFrameReorderingKey: true,
  ] as [String: Any],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
  kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
  kCVPixelBufferWidthKey as String: w,
  kCVPixelBufferHeightKey as String: h,
])
writer.add(input)
guard writer.startWriting() else {
  print("cannot start: \(String(describing: writer.error))")
  exit(1)
}
writer.startSession(atSourceTime: .zero)

let space = CGColorSpaceCreateDeviceRGB()
var written = 0
for (i, name) in names.enumerated() {
  guard let img = load(name), img.width == w, img.height == h else {
    print("\(name): not a picture of \(w) x \(h)")
    exit(1)
  }
  while !input.isReadyForMoreMediaData { usleep(2000) }
  var made: CVPixelBuffer?
  guard let pool = adaptor.pixelBufferPool,
        CVPixelBufferPoolCreatePixelBuffer(nil, pool, &made) == kCVReturnSuccess, let buf = made else {
    print("no room for picture \(i)")
    exit(1)
  }
  CVPixelBufferLockBaseAddress(buf, [])
  if let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buf), width: w, height: h, bitsPerComponent: 8,
                         bytesPerRow: CVPixelBufferGetBytesPerRow(buf), space: space,
                         bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue) {
    ctx.interpolationQuality = .none
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
  }
  CVPixelBufferUnlockBaseAddress(buf, [])
  if !adaptor.append(buf, withPresentationTime: CMTime(value: Int64(i), timescale: fps)) {
    print("picture \(i) not taken: \(String(describing: writer.error))")
    exit(1)
  }
  written += 1
}
input.markAsFinished()
writer.endSession(atSourceTime: CMTime(value: Int64(written), timescale: fps))
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
if writer.status != .completed {
  print("not finished: \(String(describing: writer.error))")
  exit(1)
}
let size = ((try? FileManager.default.attributesOfItem(atPath: out.path))?[.size] as? Int) ?? 0
print("\(written) pictures, \(w) x \(h), \(Double(written) / Double(fps)) s -> \(out.lastPathComponent), \(size) bytes")
