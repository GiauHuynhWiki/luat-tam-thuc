import Foundation
import AppKit
import ImageIO

// Check 2b of the OCR audit: ink on the page image that no OCR line and no figure box accounts for.
// Build: swiftc -O tools/verify_ink.swift -o tools/verify_ink
// Usage:
//   tools/verify_ink scan <pagesDir> <ocrDir> <figures.json> <first> <last> <out.json>
//       -> {"41": [{"box": [x, y, w, h], "kind": "text"|"blob"|"dark", "ink": 0.12}, ...]}  (normalized, top-left)
//   tools/verify_ink sheet <pagesDir> <scan.json> <outPrefix> [cols=6] [rows=3]
//       whole-page thumbnails (aspect kept) with the suspicious boxes in red, pages listed in scan.json
//   tools/verify_ink zoom <pagesDir> <scan.json> <outPrefix> [perSheet=12]
//       each suspicious box cropped with some context at full 150 DPI resolution, red frame, page no. above
// Pages darker than DARK_PAGE on average (white text on black) are inverted before scanning.

let INK: UInt8 = 150
let CELL = 4, CELL_MIN = 3
let DX = 4, DY = 1                 // dilation in cells: joins letters of a word / words of a line
let TOP = 0.065, BOTTOM = 0.935    // running head / page number + watermark bands
let MIN_W = 0.012, MIN_H = 0.007, MIN_INK = 40
let TEXT_H = 0.05                  // taller than this is not a single text line
let DARK_PAGE = 110.0

struct Line: Decodable { let x, y, w, h: Double; let text: String }
struct OCRPage: Decodable { let lines: [Line] }
typealias Box = [Double]

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
  return (buf, w, h)
}

func loadImage(_ path: String) -> CGImage? {
  guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil) else { return nil }
  return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

func savePNG(_ img: CGImage, _ path: String) {
  let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, "public.png" as CFString, 1, nil)!
  CGImageDestinationAddImage(dest, img, nil); CGImageDestinationFinalize(dest)
}

func scan(pagePng: String, ocrJson: String, figures: [Box]) -> [[String: Any]] {
  guard var page = loadGray(pagePng),
        let data = FileManager.default.contents(atPath: ocrJson),
        let ocr = try? JSONDecoder().decode(OCRPage.self, from: data) else { return [] }
  let w = page.w, h = page.h, W = Double(w), H = Double(h)
  let mean = page.buf.reduce(0.0) { $0 + Double($1) } / Double(w * h)
  if mean < DARK_PAGE { page.buf = page.buf.map { 255 - $0 } }
  var buf = page.buf
  func erase(_ x0d: Double, _ y0d: Double, _ x1d: Double, _ y1d: Double) {
    let x0 = max(0, Int(x0d * W)), x1 = min(w, Int(x1d * W)), y0 = max(0, Int(y0d * H)), y1 = min(h, Int(y1d * H))
    if x0 < x1 && y0 < y1 { for y in y0..<y1 { for x in x0..<x1 { buf[y * w + x] = 255 } } }
  }
  for l in ocr.lines { erase(l.x - 0.006, l.y - 0.4 * l.h, l.x + l.w + 0.006, l.y + 1.25 * l.h) }
  for b in figures { erase(b[0], b[1], b[0] + b[2], b[1] + b[3]) }
  erase(0, 0, 1, TOP); erase(0, BOTTOM, 1, 1)

  let gw = (w + CELL - 1) / CELL, gh = (h + CELL - 1) / CELL
  var count = [Int](repeating: 0, count: gw * gh)
  for y in 0..<h { for x in 0..<w where buf[y * w + x] < INK { count[(y / CELL) * gw + x / CELL] += 1 } }
  let ink = count.map { $0 >= CELL_MIN }
  var grown = [Bool](repeating: false, count: gw * gh)
  for cy in 0..<gh { for cx in 0..<gw where ink[cy * gw + cx] {
    for yy in max(0, cy - DY)...min(gh - 1, cy + DY) { for xx in max(0, cx - DX)...min(gw - 1, cx + DX) { grown[yy * gw + xx] = true } }
  } }
  var seen = [Bool](repeating: false, count: gw * gh)
  var out: [[String: Any]] = []
  for start in 0..<(gw * gh) where grown[start] && !seen[start] {
    var stack = [start]; seen[start] = true
    var minX = Int.max, minY = Int.max, maxX = -1, maxY = -1, px = 0
    while let c = stack.popLast() {
      let cx = c % gw, cy = c / gw
      if ink[c] { minX = min(minX, cx); minY = min(minY, cy); maxX = max(maxX, cx); maxY = max(maxY, cy); px += count[c] }
      for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
        let nx = cx + dx, ny = cy + dy
        if nx < 0 || ny < 0 || nx >= gw || ny >= gh { continue }
        let n = ny * gw + nx
        if grown[n] && !seen[n] { seen[n] = true; stack.append(n) }
      }
    }
    if maxX < 0 { continue }
    let b: Box = [Double(minX * CELL) / W, Double(minY * CELL) / H,
                  Double((maxX - minX + 1) * CELL) / W, Double((maxY - minY + 1) * CELL) / H]
    if b[2] < MIN_W || b[3] < MIN_H || px < MIN_INK { continue }
    let fill = Double(px) / (b[2] * W * b[3] * H)
    let kind = fill > 0.55 && b[2] * b[3] > 0.002 ? "dark" : (b[3] <= TEXT_H ? "text" : "blob")
    out.append(["box": b.map { ($0 * 10000).rounded() / 10000 }, "kind": kind, "ink": (fill * 100).rounded() / 100])
  }
  return out
}

let a = CommandLine.arguments
func pad3(_ n: Int) -> String { String(format: "%03d", n) }
func readScan(_ path: String) -> [String: [[String: Any]]] {
  (try? JSONSerialization.jsonObject(with: FileManager.default.contents(atPath: path)!)) as? [String: [[String: Any]]] ?? [:]
}
let red = CGColor(red: 1, green: 0, blue: 0, alpha: 1)

switch a.count > 1 ? a[1] : "" {
case "scan":
  let pages = a[2], ocr = a[3], first = Int(a[5])!, last = Int(a[6])!
  let figs = (try? JSONSerialization.jsonObject(with: FileManager.default.contents(atPath: a[4])!)) as? [String: [[Double]]] ?? [:]
  var out: [String: [[String: Any]]] = [:]
  for n in first...last {
    let r = scan(pagePng: "\(pages)/p\(pad3(n)).png", ocrJson: "\(ocr)/p\(pad3(n)).json", figures: figs[String(n)] ?? [])
    if !r.isEmpty { out[String(n)] = r }
  }
  let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys, .prettyPrinted])
  try! data.write(to: URL(fileURLWithPath: a[7]))
  print("pages with unexplained ink: \(out.count), regions: \(out.values.map { $0.count }.reduce(0, +))")

case "sheet":
  let pages = a[2], scanRes = readScan(a[3]), prefix = a[4]
  let cols = a.count > 5 ? Int(a[5])! : 6, rows = a.count > 6 ? Int(a[6])! : 3
  let cellW = 300, cellH = 440, gap = 28, per = cols * rows
  let list = scanRes.keys.compactMap { Int($0) }.sorted()
  for (k, start) in stride(from: 0, to: list.count, by: per).enumerated() {
    let chunk = Array(list[start..<min(list.count, start + per)])
    let SW = cols * (cellW + gap) + gap, SH = rows * (cellH + gap) + gap
    let ctx = CGContext(data: nil, width: SW, height: SH, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(gray: 0.85, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: SW, height: SH))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    for (i, n) in chunk.enumerated() {
      guard let img = loadImage("\(pages)/p\(pad3(n)).png") else { continue }
      let s = min(Double(cellW) / Double(img.width), Double(cellH) / Double(img.height))
      let tw = Double(img.width) * s, th = Double(img.height) * s
      let ox = Double(gap + (i % cols) * (cellW + gap)), oyTop = Double(gap + (i / cols) * (cellH + gap))
      let rect = CGRect(x: ox, y: Double(SH) - oyTop - th, width: tw, height: th)
      ctx.draw(img, in: rect)
      ctx.setStrokeColor(red); ctx.setLineWidth(2)
      for r in scanRes[String(n)]! {
        let b = r["box"] as! [Double]
        let x0: Double = Double(rect.minX) + b[0] * tw - 2, y0: Double = Double(rect.maxY) - (b[1] + b[3]) * th - 2
        ctx.stroke(CGRect(x: x0, y: y0, width: b[2] * tw + 4, height: b[3] * th + 4))
      }
      ("\(n)" as NSString).draw(at: NSPoint(x: ox, y: Double(SH) - oyTop + 4),
                                withAttributes: [.font: NSFont.boldSystemFont(ofSize: 18), .foregroundColor: NSColor.blue])
    }
    let path = "\(prefix)\(String(format: "%02d", k + 1)).png"
    savePNG(ctx.makeImage()!, path)
    print(path, chunk.first!, "-", chunk.last!)
  }

case "zoom":
  let pages = a[2], scanRes = readScan(a[3]), prefix = a[4], per = a.count > 5 ? Int(a[5])! : 12
  var items: [(Int, Box, String)] = []
  for n in scanRes.keys.compactMap({ Int($0) }).sorted() {
    for r in scanRes[String(n)]! { items.append((n, r["box"] as! [Double], r["kind"] as! String)) }
  }
  let cw = 560, ch = 150, gap = 26, cols = 2
  for (k, start) in stride(from: 0, to: items.count, by: per).enumerated() {
    let chunk = Array(items[start..<min(items.count, start + per)])
    let rows = (chunk.count + cols - 1) / cols
    let SW = cols * (cw + gap) + gap, SH = rows * (ch + gap) + gap
    let ctx = CGContext(data: nil, width: SW, height: SH, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(gray: 0.8, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: SW, height: SH))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    for (i, it) in chunk.enumerated() {
      guard let img = loadImage("\(pages)/p\(pad3(it.0)).png") else { continue }
      let W = Double(img.width), H = Double(img.height), b = it.1
      // context: the region plus margins, clipped to the page
      let cx0 = max(0, (b[0] - 0.08) * W), cy0 = max(0, (b[1] - 0.02) * H)
      let cx1 = min(W, (b[0] + b[2] + 0.08) * W), cy1 = min(H, (b[1] + b[3] + 0.02) * H)
      guard let crop = img.cropping(to: CGRect(x: cx0, y: cy0, width: cx1 - cx0, height: cy1 - cy0).integral) else { continue }
      let s = min(Double(cw) / Double(crop.width), Double(ch) / Double(crop.height), 2.0)
      let tw = Double(crop.width) * s, th = Double(crop.height) * s
      let ox = Double(gap + (i % cols) * (cw + gap)), oyTop = Double(gap + (i / cols) * (ch + gap))
      let rect = CGRect(x: ox, y: Double(SH) - oyTop - th, width: tw, height: th)
      ctx.draw(crop, in: rect)
      ctx.setStrokeColor(red); ctx.setLineWidth(2)
      let fx: Double = Double(rect.minX) + (b[0] * W - cx0) * s - 2
      let fy: Double = Double(rect.maxY) - ((b[1] + b[3]) * H - cy0) * s - 2
      ctx.stroke(CGRect(x: fx, y: fy, width: b[2] * W * s + 4, height: b[3] * H * s + 4))
      ("p\(it.0) \(it.2) y=\(String(format: "%.2f", b[1]))" as NSString).draw(at: NSPoint(x: ox, y: Double(SH) - oyTop + 3),
        withAttributes: [.font: NSFont.boldSystemFont(ofSize: 15), .foregroundColor: NSColor.blue])
    }
    let path = "\(prefix)\(String(format: "%02d", k + 1)).png"
    savePNG(ctx.makeImage()!, path)
    print(path, chunk.count)
  }

default:
  print("usage: verify_ink scan|sheet|zoom … (see header)")
}
