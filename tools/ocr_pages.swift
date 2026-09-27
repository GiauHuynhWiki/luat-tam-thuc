import Vision
import AppKit
// OCR rendered page PNGs with macOS Vision (Vietnamese) and dump raw lines as JSON.
// Build: swiftc -O tools/ocr_pages.swift -o tools/ocr_pages
// Usage: tools/ocr_pages <pagesdir> <outdir> <firstPage> <lastPage> [footer]  -> <outdir>/p041.json
//   footer: only read the bottom 10% of the page, down to very small text (page numbers).
// JSON: {"page":41,"width":837,"height":1331,"lines":[{"text":…,"conf":0.5,"x":…,"y":…,"w":…,"h":…}]}
// Coordinates are normalized 0–1 over the whole page, origin at the TOP-left (Vision's y is flipped here).
let a = CommandLine.arguments
let pagesDir = a[1], out = a[2], first = Int(a[3])!, last = Int(a[4])!
let footer = a.count > 5 && a[5] == "footer"
let roi = footer ? CGRect(x: 0, y: 0, width: 1, height: 0.1) : CGRect(x: 0, y: 0, width: 1, height: 1)
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)

for n in first...last {
  let src = String(format: "%@/p%03d.png", pagesDir, n)
  guard let img = NSImage(contentsOfFile: src),
        let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("missing \(src)\n".data(using: .utf8)!)
    continue
  }
  let req = VNRecognizeTextRequest()
  req.recognitionLevel = .accurate
  req.recognitionLanguages = ["vi-VT"]
  req.usesLanguageCorrection = true
  req.regionOfInterest = roi
  if footer { req.minimumTextHeight = 0.1 }
  try! VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])

  var lines: [[String: Any]] = []
  for obs in req.results ?? [] {
    guard let top = obs.topCandidates(1).first else { continue }
    // boundingBox is relative to the region of interest; map it back to the whole page
    let r = obs.boundingBox
    let b = CGRect(x: roi.minX + r.minX * roi.width, y: roi.minY + r.minY * roi.height,
                   width: r.width * roi.width, height: r.height * roi.height)
    lines.append([
      "text": top.string, "conf": Double(top.confidence),
      "x": Double(b.minX), "y": Double(1 - b.maxY), "w": Double(b.width), "h": Double(b.height),
    ])
  }
  let obj: [String: Any] = ["page": n, "width": cg.width, "height": cg.height, "lines": lines]
  let data = try! JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys])
  try! data.write(to: URL(fileURLWithPath: String(format: "%@/p%03d.json", out, n)))
  print(n, lines.count)
}
