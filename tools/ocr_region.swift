import Foundation
import AppKit
import ImageIO
import Vision

// Re-OCR one region of a page image with Vision, for the fixes in tools/ocr_fix/ (see tools/ocr_fix.py).
// Build: swiftc -O tools/ocr_region.swift -o tools/ocr_region
// Usage:
//   tools/ocr_region ocr <page.png> <x> <y> <w> <h> [scale=2] [invert=0]
//       crop the box (normalized, top-left origin), enlarge it `scale` times, optionally invert (white on
//       black), OCR with Vision (vi-VT, .accurate, language correction)
//       -> {"lines": [{"text", "conf", "x", "y", "w", "h"}]}, coordinates normalized over the WHOLE page
//   tools/ocr_region dropcap <page.png> <x0> <y0> <x1> <y1>
//       the tallest ink blob in the box (the drop cap), and the text-line bands to its right
//       -> {"cap": [x, y, w, h], "bands": [[y, h], ...]}
//   tools/ocr_region dropcap-ocr <page.png> <x0> <y0> <x1> <y1> [scale=2] [debugPrefix]
//       OCR the (up to) two lines beside a drop cap: each line band is cut from the cap's left edge to the
//       box's right edge with the cap's own pixels whitened; for the first line the cap, shrunk to the
//       line's capital height, is drawn back just before the line's first letter, so the first word is
//       read whole. -> {"cap": [...], "lines": [{"text", "conf", "x", "y", "w", "h"}]} (page-normalized)

let INK: UInt8 = 150

func loadImage(_ path: String) -> CGImage {
  let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil)!
  return CGImageSourceCreateImageAtIndex(src, 0, nil)!
}

func gray(_ img: CGImage) -> [UInt8] {
  let w = img.width, h = img.height
  var buf = [UInt8](repeating: 255, count: w * h)
  buf.withUnsafeMutableBytes { p in
    let ctx = CGContext(data: p.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w,
                        space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
  }
  return buf // row 0 = top
}

func emit(_ obj: Any) {
  let data = try! JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])
  print(String(data: data, encoding: .utf8)!)
}

let a = CommandLine.arguments
switch a.count > 1 ? a[1] : "" {
case "ocr":
  let img = loadImage(a[2])
  let bx = Double(a[3])!, by = Double(a[4])!, bw = Double(a[5])!, bh = Double(a[6])!
  let scale = a.count > 7 ? Double(a[7])! : 2, invert = a.count > 8 && a[8] == "1"
  let W = Double(img.width), H = Double(img.height)
  let crop = img.cropping(to: CGRect(x: bx * W, y: by * H, width: bw * W, height: bh * H).integral)!
  let cw = Int(Double(crop.width) * scale), ch = Int(Double(crop.height) * scale)
  let ctx = CGContext(data: nil, width: cw, height: ch, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
  ctx.interpolationQuality = .high
  ctx.setFillColor(gray: 1, alpha: 1)
  ctx.fill(CGRect(x: 0, y: 0, width: cw, height: ch))
  ctx.draw(crop, in: CGRect(x: 0, y: 0, width: cw, height: ch))
  if invert {
    ctx.setBlendMode(.difference)
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: cw, height: ch))
  }
  let big = ctx.makeImage()!
  let req = VNRecognizeTextRequest()
  req.recognitionLevel = .accurate
  req.recognitionLanguages = ["vi-VT"]
  req.usesLanguageCorrection = true
  try! VNImageRequestHandler(cgImage: big, options: [:]).perform([req])
  // the crop's pixel box, normalized over the page (integral() may have moved it slightly)
  let cx = Double(crop.width) / W, cy = Double(crop.height) / H
  let ox = (bx * W).rounded(.down) / W, oy = (by * H).rounded(.down) / H
  var lines: [[String: Any]] = []
  for obs in req.results ?? [] {
    guard let top = obs.topCandidates(1).first else { continue }
    let r = obs.boundingBox // normalized over the crop, origin bottom-left
    lines.append(["text": top.string, "conf": Double(top.confidence),
                  "x": ox + r.minX * cx, "y": oy + (1 - r.maxY) * cy, "w": r.width * cx, "h": r.height * cy])
  }
  emit(["lines": lines])

case "dropcap", "dropcap-ocr":
  let img = loadImage(a[2])
  let w = img.width, h = img.height, W = Double(w), H = Double(h)
  let buf = gray(img)
  let x0 = Int(Double(a[3])! * W), y0 = Int(Double(a[4])! * H), x1 = Int(Double(a[5])! * W), y1 = Int(Double(a[6])! * H)
  // connected ink components (4-neighbour) inside the box
  var seen = [Bool](repeating: false, count: w * h)
  var best = (minX: 0, minY: 0, maxX: -1, maxY: -1)
  var bestPixels: [Int] = []
  for sy in y0..<y1 { for sx in x0..<x1 where buf[sy * w + sx] < INK && !seen[sy * w + sx] {
    var stack = [sy * w + sx]; seen[sy * w + sx] = true
    var r = (minX: sx, minY: sy, maxX: sx, maxY: sy)
    var pixels: [Int] = []
    while let c = stack.popLast() {
      let cx = c % w, cy = c / w
      pixels.append(c)
      r = (min(r.minX, cx), min(r.minY, cy), max(r.maxX, cx), max(r.maxY, cy))
      for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
        let nx = cx + dx, ny = cy + dy
        if nx < x0 || ny < y0 || nx >= x1 || ny >= y1 { continue }
        let n = ny * w + nx
        if buf[n] < INK && !seen[n] { seen[n] = true; stack.append(n) }
      }
    }
    if r.maxY - r.minY > best.maxY - best.minY { best = r; bestPixels = pixels }
  } }
  // text bands right of the cap: rows with ink, merged over small gaps
  var bands: [[Double]] = []
  let tx0 = best.maxX + Int(0.01 * W)
  var start = -1, gapRun = 0
  let rowsTop = max(0, best.minY - Int(0.01 * H)), rowsBot = min(h, best.maxY + Int(0.01 * H))
  for y in rowsTop..<rowsBot {
    var n = 0
    for x in tx0..<x1 where buf[y * w + x] < INK { n += 1 }
    if n > 3 { if start < 0 { start = y }; gapRun = 0 } else if start >= 0 {
      gapRun += 1
      if gapRun > Int(0.003 * H) {
        let end = y - gapRun
        if Double(end - start) > 0.008 * H { bands.append([Double(start) / H, Double(end - start) / H]) }
        start = -1; gapRun = 0
      }
    }
  }
  if start >= 0 { bands.append([Double(start) / H, Double(rowsBot - start) / H]) }
  let capBox = [Double(best.minX) / W, Double(best.minY) / H,
                Double(best.maxX - best.minX + 1) / W, Double(best.maxY - best.minY + 1) / H]
  if a[1] == "dropcap" { emit(["cap": capBox, "bands": bands]); break }

  let scale = a.count > 7 ? Double(a[7])! : 2
  let debug = a.count > 8 ? a[8] : ""
  // whiten the cap and its anti-aliased halo; CAP_KEEP=f treats only the cap's left part (fraction f
  // of its width) as the cap: its right tips can touch the first letter of line 2 (X on p372)
  let keep = Double(ProcessInfo.processInfo.environment["CAP_KEEP"] ?? "") ?? 1.0
  var clean = buf, cleanLower = buf
  let cut = best.minX + Int(Double(best.maxX - best.minX + 1) * keep)
  for c in bestPixels {
    let cx = c % w, cy = c / w
    // the cap's own pixels, plus the light-gray halo around them (never the dark ink of a neighbour)
    for yy in max(0, cy - 2)...min(h - 1, cy + 2) { for xx in max(0, cx - 2)...min(w - 1, cx + 2)
        where (xx == cx && yy == cy) || (buf[yy * w + xx] >= INK && buf[yy * w + xx] < 240) {
      clean[yy * w + xx] = 255
      if cx < cut { cleanLower[yy * w + xx] = 255 }
    } }
  }
  // the cap alone, as a gray image
  let capW = best.maxX - best.minX + 1, capH = best.maxY - best.minY + 1
  var capBuf = [UInt8](repeating: 255, count: capW * capH)
  for c in bestPixels where c % w < cut { capBuf[(c / w - best.minY) * capW + (c % w - best.minX)] = buf[c] }
  func grayImage(_ b: [UInt8], _ bw: Int, _ bh: Int) -> CGImage {
    let ctx = CGContext(data: nil, width: bw, height: bh, bitsPerComponent: 8, bytesPerRow: bw,
                        space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    b.withUnsafeBytes { memcpy(ctx.data!, $0.baseAddress!, bw * bh) }
    return ctx.makeImage()!
  }
  let capImg = grayImage(capBuf, capW, capH)
  var lines: [[String: Any]] = []
  for (i, band) in bands.filter({ $0[1] >= 0.01 }).prefix(2).enumerated() {
    let bx0 = best.minX, bx1 = x1
    let by0 = max(0, Int((band[0] - 0.006) * H)), by1 = min(h, Int((band[0] + band[1] + 0.006) * H))
    let bw = bx1 - bx0, bh = by1 - by0
    var bandBuf = [UInt8](repeating: 255, count: bw * bh)
    let src = i == 0 ? clean : cleanLower
    for y in 0..<bh { for x in 0..<bw { bandBuf[y * bw + x] = src[(y + by0) * w + x + bx0] } }
    // first ink column of the line once the cap is gone
    var first = bw
    for x in 0..<bw where first == bw { for y in 0..<bh where bandBuf[y * bw + x] < INK { first = x; break } }
    let cw = Int(Double(bw) * scale), ch = Int(Double(bh) * scale)
    let ctx = CGContext(data: nil, width: cw, height: ch, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    ctx.interpolationQuality = .high
    ctx.setFillColor(gray: 1, alpha: 1); ctx.fill(CGRect(x: 0, y: 0, width: cw, height: ch))
    ctx.draw(grayImage(bandBuf, bw, bh), in: CGRect(x: 0, y: 0, width: cw, height: ch))
    if i == 0 {
      // capital height ~ 70% of the band (band = accents + cap height + descenders); baseline ~ 78% down
      let th = Double(bh) * 0.62 * scale, tw = th * Double(capW) / Double(capH)
      let gap = th * 0.04
      let right = Double(first) * scale - gap
      let baseline = Double(bh) * 0.78 * scale  // from top
      ctx.setFillColor(gray: 1, alpha: 1)
      ctx.draw(capImg, in: CGRect(x: right - tw, y: Double(ch) - baseline, width: tw, height: th))
    }
    let comp = ctx.makeImage()!
    if !debug.isEmpty {
      let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: "\(debug)\(i + 1).png") as CFURL, "public.png" as CFString, 1, nil)!
      CGImageDestinationAddImage(dest, comp, nil); CGImageDestinationFinalize(dest)
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["vi-VT"]
    req.usesLanguageCorrection = true
    try! VNImageRequestHandler(cgImage: comp, options: [:]).perform([req])
    let obs = (req.results ?? []).compactMap { o in o.topCandidates(1).first.map { (o.boundingBox, $0) } }
      .sorted { $0.0.minX < $1.0.minX }
    let text = obs.map { $0.1.string }.joined(separator: " ")
    let conf = obs.map { Double($0.1.confidence) }.min() ?? 0
    let lx = Double(i == 0 ? best.minX : bx0 + first) / W
    lines.append(["text": text, "conf": conf, "x": lx, "y": band[0], "w": Double(bx1) / W - lx, "h": band[1]])
  }
  emit(["cap": capBox, "lines": lines])

default:
  print("usage: ocr_region ocr|dropcap … (see header)")
}
