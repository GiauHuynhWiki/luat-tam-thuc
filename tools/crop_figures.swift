import Foundation
import PDFKit
import AppKit
import ImageIO

// Find illustration regions on the scanned pages and crop them out.
// Build: swiftc -O tools/crop_figures.swift -o tools/crop_figures
// Usage:
//   tools/crop_figures detect <pagesDir> <ocrDir> <first> <last> <out.json>
//       pagesDir: 150 DPI renders pNNN.png; ocrDir: Vision OCR pNNN.json (normalized, top-left origin)
//       -> {"41": [[x, y, w, h], ...], ...}  normalized boxes, top-left origin
//   tools/crop_figures crop <pdf> <jobs.json> [dpi=300] [quality=0.9]
//       jobs: [{"page": 41, "box": [x, y, w, h], "out": "hinh/01/p041-1.jpg"}, ...]
//   tools/crop_figures sheet <pagesDir> <boxes.json> <first> <last> <outPrefix> [cols=8] [rows=4]
//       contact sheets of page thumbnails with the boxes drawn in red, for review (first=last=0: pages listed in boxes.json)

// Detection works on the 150 DPI render: erase the OCR boxes of body text, running head, page
// number and watermark, grid the remaining ink, merge nearby ink into regions, keep regions that
// are big enough and not just short text.
let INK: UInt8 = 170          // gray level below which a pixel counts as ink
let CELL = 6                  // grid cell size in px
let CELL_MIN = 4              // ink pixels a cell needs
let DILATE = 3                // cells; merges the parts of one figure
let MIN_AREA = 0.012          // of the page
let MIN_W = 0.08, MIN_H = 0.035
let BODY_W = 0.28             // an OCR line wider than this is body text
let BODY_CHARS = 22           // ... or longer than this
let TOP = 0.07, BOTTOM = 0.93 // regions entirely above/below these are running head / page number / watermark
let TEXT_ONLY = Double(ProcessInfo.processInfo.environment["TEXT_ONLY"] ?? "") ?? 0.85 // regions whose ink lies this much inside OCR boxes are text, not figures
let LABEL_REACH = 0.025       // short OCR lines this close to a region are its labels
let PAD = 0.012

struct Line: Decodable { let x, y, w, h: Double; let text: String }
struct OCRPage: Decodable { let lines: [Line] }
struct Job: Decodable { let page: Int; let box: [Double]; let out: String }

typealias Box = [Double] // x, y, w, h

func loadGray(_ path: String) -> (buf: [UInt8], w: Int, h: Int)? {
  guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
        let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { return nil }
  let w = img.width, h = img.height
  var buf = [UInt8](repeating: 255, count: w * h)
  buf.withUnsafeMutableBytes { p in
    let ctx = CGContext(data: p.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w,
                        space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
  }
  return (buf, w, h) // row 0 = top of the image
}

func union(_ a: Box, _ b: Box) -> Box {
  let x0 = min(a[0], b[0]), y0 = min(a[1], b[1])
  return [x0, y0, max(a[0] + a[2], b[0] + b[2]) - x0, max(a[1] + a[3], b[1] + b[3]) - y0]
}
func overlaps(_ a: Box, _ b: Box, _ m: Double = 0) -> Bool {
  a[0] - m < b[0] + b[2] && b[0] - m < a[0] + a[2] && a[1] - m < b[1] + b[3] && b[1] - m < a[1] + a[3]
}
func contains(_ a: Box, _ px: Double, _ py: Double, _ m: Double = 0) -> Bool {
  px >= a[0] - m && px <= a[0] + a[2] + m && py >= a[1] - m && py <= a[1] + a[3] + m
}

func detect(pagePng: String, ocrJson: String) -> [Box] {
  guard let page = loadGray(pagePng),
        let data = FileManager.default.contents(atPath: ocrJson),
        let ocr = try? JSONDecoder().decode(OCRPage.self, from: data) else { return [] }
  var buf = page.buf
  let w = page.w, h = page.h
  let W = Double(w), H = Double(h)
  var labels: [Box] = []
  for l in ocr.lines {
    let lower = l.text.lowercased()
    let site = lower.contains("kindle") || lower.contains(".com") // the scan site's watermark, never a figure label
    let body = site || l.w > BODY_W || l.text.count >= BODY_CHARS || l.y < TOP || l.y + l.h > BOTTOM
    if !body { labels.append([l.x, l.y, l.w, l.h]); continue }
    // erase with room for stacked Vietnamese diacritics above and descenders below
    let x0 = max(0, Int((l.x - 0.005) * W)), x1 = min(w, Int((l.x + l.w + 0.005) * W))
    let y0 = max(0, Int((l.y - 0.35 * l.h) * H)), y1 = min(h, Int((l.y + 1.2 * l.h) * H))
    if x0 < x1 && y0 < y1 { for y in y0..<y1 { for x in x0..<x1 { buf[y * w + x] = 255 } } }
  }
  let gw = (w + CELL - 1) / CELL, gh = (h + CELL - 1) / CELL
  var count = [Int](repeating: 0, count: gw * gh)
  for y in 0..<h { for x in 0..<w where buf[y * w + x] < INK { count[(y / CELL) * gw + x / CELL] += 1 } }
  let ink = count.map { $0 >= CELL_MIN }
  var grown = [Bool](repeating: false, count: gw * gh)
  for cy in 0..<gh { for cx in 0..<gw where ink[cy * gw + cx] {
    for yy in max(0, cy - DILATE)...min(gh - 1, cy + DILATE) {
      for xx in max(0, cx - DILATE)...min(gw - 1, cx + DILATE) { grown[yy * gw + xx] = true }
    }
  } }
  var label = [Int](repeating: -1, count: gw * gh)
  var regions: [(minX: Int, minY: Int, maxX: Int, maxY: Int, cells: [Int])] = []
  for start in 0..<(gw * gh) where grown[start] && label[start] < 0 {
    let id = regions.count
    var stack = [start], cells: [Int] = []
    label[start] = id
    var r = (minX: Int.max, minY: Int.max, maxX: -1, maxY: -1)
    while let c = stack.popLast() {
      let cx = c % gw, cy = c / gw
      if ink[c] { cells.append(c); r = (min(r.minX, cx), min(r.minY, cy), max(r.maxX, cx), max(r.maxY, cy)) }
      for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
        let nx = cx + dx, ny = cy + dy
        if nx < 0 || ny < 0 || nx >= gw || ny >= gh { continue }
        let n = ny * gw + nx
        if grown[n] && label[n] < 0 { label[n] = id; stack.append(n) }
      }
    }
    regions.append((r.minX, r.minY, r.maxX, r.maxY, cells))
  }
  var boxes: [Box] = []
  for r in regions where !r.cells.isEmpty {
    var b: Box = [Double(r.minX * CELL) / W, Double(r.minY * CELL) / H,
                  Double((r.maxX - r.minX + 1) * CELL) / W, Double((r.maxY - r.minY + 1) * CELL) / H]
    if b[1] + b[3] < TOP || b[1] > BOTTOM { continue }
    // pull in the short text lines that label this figure
    for l in labels where contains(b, l[0] + l[2] / 2, l[1] + l[3] / 2, LABEL_REACH) { b = union(b, l) }
    if b[2] * b[3] < MIN_AREA || b[2] < MIN_W || b[3] < MIN_H { continue }
    let inText = r.cells.filter { c in
      let px = (Double(c % gw) + 0.5) * Double(CELL) / W, py = (Double(c / gw) + 0.5) * Double(CELL) / H
      return labels.contains { contains($0, px, py, 0.004) }
    }.count
    if Double(inText) / Double(r.cells.count) > TEXT_ONLY { continue }
    boxes.append(b)
  }
  // merge regions that touch once padded, then pad and clamp
  var merged = true
  while merged {
    merged = false
    outer: for i in 0..<boxes.count { for j in (i + 1)..<max(i + 1, boxes.count) where overlaps(boxes[i], boxes[j], PAD) {
      boxes[i] = union(boxes[i], boxes[j]); boxes.remove(at: j); merged = true; break outer
    } }
  }
  return boxes.sorted { ($0[1], $0[0]) < ($1[1], $1[0]) }.map { b in
    let x0 = max(0, b[0] - PAD), y0 = max(0, b[1] - PAD)
    return [x0, y0, min(1, b[0] + b[2] + PAD) - x0, min(1, b[1] + b[3] + PAD) - y0].map { ($0 * 10000).rounded() / 10000 }
  }
}

func render(_ page: PDFPage, dpi: CGFloat) -> CGImage {
  let box = page.bounds(for: .mediaBox), s = dpi / 72
  let w = Int(box.width * s), h = Int(box.height * s)
  let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
  ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
  ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
  ctx.scaleBy(x: s, y: s)
  page.draw(with: .mediaBox, to: ctx)
  return ctx.makeImage()!
}

func writeJPEG(_ img: CGImage, _ path: String, _ quality: Double) {
  try? FileManager.default.createDirectory(atPath: (path as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
  let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, "public.jpeg" as CFString, 1, nil)!
  CGImageDestinationAddImage(dest, img, [kCGImageDestinationLossyCompressionQuality: quality] as CFDictionary)
  CGImageDestinationFinalize(dest)
}

let a = CommandLine.arguments
func pad3(_ n: Int) -> String { String(format: "%03d", n) }

switch a.count > 1 ? a[1] : "" {
case "detect":
  let pages = a[2], ocr = a[3], first = Int(a[4])!, last = Int(a[5])!
  var out: [String: [Box]] = [:]
  for n in first...last {
    let b = detect(pagePng: "\(pages)/p\(pad3(n)).png", ocrJson: "\(ocr)/p\(pad3(n)).json")
    if !b.isEmpty { out[String(n)] = b }
  }
  let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
  try! data.write(to: URL(fileURLWithPath: a[6]))
  print("pages with figures: \(out.count), boxes: \(out.values.map { $0.count }.reduce(0, +))")

case "crop":
  let doc = PDFDocument(url: URL(fileURLWithPath: a[2]))!
  let jobs = try! JSONDecoder().decode([Job].self, from: FileManager.default.contents(atPath: a[3])!)
  let dpi = a.count > 4 ? CGFloat(Double(a[4])!) : 300, q = a.count > 5 ? Double(a[5])! : 0.9
  for (page, group) in Dictionary(grouping: jobs, by: { $0.page }).sorted(by: { $0.key < $1.key }) {
    let img = render(doc.page(at: page - 1)!, dpi: dpi)
    let W = Double(img.width), H = Double(img.height)
    for j in group {
      let r = CGRect(x: j.box[0] * W, y: j.box[1] * H, width: j.box[2] * W, height: j.box[3] * H).integral
      if let c = img.cropping(to: r) { writeJPEG(c, j.out, q) }
    }
  }
  print("cropped \(jobs.count) figures")

case "sheet":
  let pages = a[2], first = Int(a[4])!, last = Int(a[5])!, prefix = a[6]
  let cols = a.count > 7 ? Int(a[7])! : 8, rows = a.count > 8 ? Int(a[8])! : 4
  let boxes = (try? JSONSerialization.jsonObject(with: FileManager.default.contents(atPath: a[3])!)) as? [String: [[Double]]] ?? [:]
  let tw = 180, th = 286, gap = 24, per = cols * rows
  let list = first == 0 ? boxes.keys.compactMap { Int($0) }.sorted() : Array(first...last) // 0 0: only pages in boxes.json
  for (k, start) in stride(from: 0, to: list.count, by: per).enumerated() {
    let chunk = Array(list[start..<min(list.count, start + per)])
    let SW = cols * (tw + gap) + gap, SH = rows * (th + gap) + gap
    let ctx = CGContext(data: nil, width: SW, height: SH, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(gray: 0.85, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: SW, height: SH))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    for (i, n) in chunk.enumerated() {
      let ox = gap + (i % cols) * (tw + gap), oyTop = gap + (i / cols) * (th + gap)
      let rect = CGRect(x: ox, y: SH - oyTop - th, width: tw, height: th)
      if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: "\(pages)/p\(pad3(n)).png") as CFURL, nil),
         let img = CGImageSourceCreateImageAtIndex(src, 0, nil) { ctx.draw(img, in: rect) }
      ctx.setStrokeColor(CGColor(red: 1, green: 0, blue: 0, alpha: 1)); ctx.setLineWidth(2)
      for b in boxes[String(n)] ?? [] {
        ctx.stroke(CGRect(x: rect.minX + b[0] * Double(tw), y: rect.maxY - (b[1] + b[3]) * Double(th),
                          width: b[2] * Double(tw), height: b[3] * Double(th)))
      }
      ("\(n)" as NSString).draw(at: NSPoint(x: ox, y: SH - oyTop + 2),
                                withAttributes: [.font: NSFont.boldSystemFont(ofSize: 15), .foregroundColor: NSColor.blue])
    }
    let path = "\(prefix)\(String(format: "%02d", k + 1)).png"
    let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil); CGImageDestinationFinalize(dest)
    print(path, chunk.first!, "-", chunk.last!)
  }

default:
  print("usage: crop_figures detect|crop|sheet … (see header)")
}
