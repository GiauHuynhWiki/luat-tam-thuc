import PDFKit
import AppKit
// Render PDF pages to PNG with macOS PDFKit (no poppler needed).
// Build: swiftc -O tools/render_pages.swift -o tools/render_pages
// Usage: tools/render_pages <pdf> <outdir> <firstPage> <lastPage> [dpi=150]  -> <outdir>/p041.png
let a = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: a[1]))!
let out = a[2], first = Int(a[3])!, last = Int(a[4])!
let dpi = a.count > 5 ? CGFloat(Double(a[5])!) : 150
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
for n in first...min(last, doc.pageCount) {
  let page = doc.page(at: n - 1)!
  let box = page.bounds(for: .mediaBox)
  let s = dpi / 72
  let w = Int(box.width * s), h = Int(box.height * s)
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.saveGraphicsState()
  let ctx = NSGraphicsContext(bitmapImageRep: rep)!
  NSGraphicsContext.current = ctx
  ctx.cgContext.setFillColor(NSColor.white.cgColor)
  ctx.cgContext.fill(CGRect(x: 0, y: 0, width: w, height: h))
  ctx.cgContext.scaleBy(x: s, y: s)
  page.draw(with: .mediaBox, to: ctx.cgContext)
  NSGraphicsContext.restoreGraphicsState()
  let path = String(format: "%@/p%03d.png", out, n)
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
  print(path, w, "x", h)
}
