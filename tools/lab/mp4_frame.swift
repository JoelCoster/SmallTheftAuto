// One picture out of a video, to look at what the video writer made of it.
//
//   swift tools/lab/mp4_frame.swift <video> <seconds> <out.png>
import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 4, let at = Double(args[2]) else {
  print("usage: mp4_frame <video> <seconds> <out.png>")
  exit(1)
}
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let gen = AVAssetImageGenerator(asset: asset)
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
gen.appliesPreferredTrackTransform = true
let done = DispatchSemaphore(value: 0)
gen.generateCGImageAsynchronously(for: CMTime(seconds: at, preferredTimescale: 600)) { img, _, err in
  if let img = img,
     let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[3]) as CFURL, UTType.png.identifier as CFString, 1, nil) {
    CGImageDestinationAddImage(dst, img, nil)
    CGImageDestinationFinalize(dst)
    print("\(img.width) x \(img.height) at \(at) s -> \(args[3])")
  } else {
    print("no picture: \(String(describing: err))")
  }
  done.signal()
}
done.wait()
