//go:build ignore

// Генератор демо-картинок номенклатуры для конфигурации trade.
//
// Рисует 13 flat-иконок мебели на пастельных карточках (300×300 PNG) — по одной
// на каждый демо-товар из src/заполнитьтестовуюбазу.proc.os. Только стандартная
// библиотека Go (image/draw, image/png), без шрифтов и внешних зависимостей.
//
// Запуск из корня репо конфигурации:
//
//	go run scripts/gen_demo_images.go
//
// Что делает:
//   - сохраняет PNG в scripts/demo_images/<артикул>.png (для просмотра/правок);
//   - печатает в scripts/demo_images/_imgvars.os.txt блок присваивания
//     переменных с Base64 — он вставляется в демо-обработку (реквизит
//     ОсновноеИзображение заполняется через СохранитьКартинку).
//
// Чтобы перерисовать картинки — отредактируйте drawXxx ниже и перезапустите.
package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"math"
	"os"
	"path/filepath"
	"sort"
)

const S = 300 // размер карточки

// продукт: артикул (ключ сшивки с .os) → суффикс имени переменной + тип иконки.
type product struct {
	art  string // артикул из демо-обработки
	suf  string // суффикс переменной Фото<...> (как Ном<...> в обработке)
	kind string // тип иконки
}

var products = []product{
	{"TAB-2000", "Табурет", "stool"},
	{"KRS-BOSS", "Кресло", "chair"},
	{"STL-WTF", "Стол", "table"},
	{"DIV-SOFT", "Диван", "sofa"},
	{"PLK-PIZA", "Полка", "shelf"},
	{"PUF-CUBE", "Пуф", "pouf"},
	{"SHK-SECR", "Шкаф", "wardrobe"},
	{"KMD-HEST", "Комод", "dresser"},
	{"TMB-NITE", "Тумбочка", "nightstand"},
	{"KRV-SLEP", "Кровать", "bed"},
	{"STL-BOOK", "Стеллаж", "bookshelf"},
	{"BNK-GILT", "Банкетка", "bench"},
	{"NAB-TBL", "Набор", "diningset"},
}

func main() {
	outDir := filepath.Join("scripts", "demo_images")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		panic(err)
	}

	// Имена переменных по убыванию длины — для аккуратного выравнивания = в .os.
	sufs := make([]string, len(products))
	for i, p := range products {
		sufs[i] = p.suf
	}
	sort.Slice(sufs, func(i, j int) bool { return len(sufs[i]) > len(sufs[j]) })
	maxLen := len("Фото" + sufs[0])

	var buf bytes.Buffer
	fmt.Fprintln(&buf, "  // Демо-картинки номенклатуры. Сгенерировано scripts/gen_demo_images.go")
	fmt.Fprintln(&buf, "  // (перерисовать: go run scripts/gen_demo_images.go). Base64 иконок мебели 300×300.")
	for i, p := range products {
		img := render(p.kind, i)
		var pngBuf bytes.Buffer
		if err := png.Encode(&pngBuf, img); err != nil {
			panic(err)
		}
		pngPath := filepath.Join(outDir, p.art+".png")
		if err := os.WriteFile(pngPath, pngBuf.Bytes(), 0o644); err != nil {
			panic(err)
		}
		b64 := base64.StdEncoding.EncodeToString(pngBuf.Bytes())
		name := "Фото" + p.suf
		fmt.Fprintf(&buf, "  %s%s = \"%s\";\n", name, spaces(maxLen-len(name)), b64)
	}
	outPath := filepath.Join(outDir, "_imgvars.os.txt")
	if err := os.WriteFile(outPath, buf.Bytes(), 0o644); err != nil {
		panic(err)
	}
	fmt.Println("written:", outPath)
	fmt.Println("pngs:", outDir)
}

func spaces(n int) string {
	if n < 0 {
		n = 0
	}
	b := make([]byte, n)
	for i := range b {
		b[i] = ' '
	}
	return string(b)
}

// render собирает карточку: пастельный фон + мягкая тень + иконка мебели.
func render(kind string, idx int) *image.RGBA {
	img := image.NewRGBA(image.Rect(0, 0, S, S))
	hue := float64(idx) * (360.0 / float64(len(products)))
	bg := hsl(hue, 0.42, 0.90)
	accent := hsl(hue, 0.50, 0.45)
	dark := hsl(hue, 0.55, 0.32)
	light := hsl(hue, 0.45, 0.97)

	draw.Draw(img, img.Bounds(), &image.Uniform{bg}, image.Point{}, draw.Src)
	// лёгкая «пол»-тень под предметом
	fillEllipse(img, 150, 262, 110, 14, color.RGBA{0, 0, 0, 26})

	drawIcon(img, kind, accent, dark, light)
	return img
}

func drawIcon(img *image.RGBA, kind string, accent, dark, light color.RGBA) {
	switch kind {
	case "stool":
		drawStool(img, accent, dark)
	case "chair":
		drawChair(img, accent, dark)
	case "table":
		drawTable(img, accent, dark)
	case "sofa":
		drawSofa(img, accent, dark, light)
	case "shelf":
		drawShelf(img, accent, dark)
	case "pouf":
		drawPouf(img, accent, dark)
	case "wardrobe":
		drawWardrobe(img, accent, dark)
	case "dresser":
		drawDresser(img, accent, dark)
	case "nightstand":
		drawNightstand(img, accent, dark)
	case "bed":
		drawBed(img, accent, dark, light)
	case "bookshelf":
		drawBookshelf(img, accent, dark)
	case "bench":
		drawBench(img, accent, dark)
	case "diningset":
		drawDiningSet(img, accent, dark)
	}
}

// ─── иконки ────────────────────────────────────────────────────────────────

func drawStool(img *image.RGBA, c, d color.RGBA) {
	// ножки
	for _, lg := range [][4]int{{116, 168, 96, 240}, {184, 168, 204, 240}, {134, 172, 126, 240}, {166, 172, 174, 240}} {
		thickLine(img, lg[0], lg[1], lg[2], lg[3], 10, d)
	}
	// сиденье
	fillCircle(img, 150, 140, 56, d)
	fillCircle(img, 150, 138, 48, c)
}

func drawChair(img *image.RGBA, c, d color.RGBA) {
	// ножки
	thickLine(img, 92, 205, 84, 250, 9, d)
	thickLine(img, 208, 205, 216, 250, 9, d)
	// подлокотники
	fillRect(img, 68, 150, 94, 205, d)
	fillRect(img, 206, 150, 232, 205, d)
	fillRoundRect(img, 70, 148, 92, 200, 8, c)
	fillRoundRect(img, 208, 148, 230, 200, 8, c)
	// сиденье
	fillRoundRect(img, 80, 150, 220, 205, 12, c)
	// спинка
	fillRoundRect(img, 92, 66, 208, 150, 16, d)
	fillRoundRect(img, 100, 74, 200, 146, 12, c)
}

func drawTable(img *image.RGBA, c, d color.RGBA) {
	fillRect(img, 52, 122, 248, 150, d)
	fillRect(img, 56, 126, 244, 146, c)
	// ножки
	thickLine(img, 76, 150, 70, 246, 11, d)
	thickLine(img, 224, 150, 230, 246, 11, d)
	thickLine(img, 150, 150, 150, 246, 9, shade(d, -10))
}

func drawSofa(img *image.RGBA, c, d, l color.RGBA) {
	// основание
	fillRoundRect(img, 40, 150, 260, 238, 18, d)
	fillRoundRect(img, 46, 156, 254, 232, 14, c)
	// спинка
	fillRoundRect(img, 40, 86, 260, 168, 20, d)
	fillRoundRect(img, 48, 94, 252, 162, 14, c)
	// подлокотники
	fillRoundRect(img, 28, 120, 60, 238, 14, d)
	fillRoundRect(img, 240, 120, 272, 238, 14, d)
	// швы подушек
	thickLine(img, 120, 98, 120, 160, 4, shade(d, -8))
	thickLine(img, 180, 98, 180, 160, 4, shade(d, -8))
	// подушки-акцент
	fillRoundRect(img, 60, 170, 120, 224, 10, l)
	fillRoundRect(img, 180, 170, 240, 224, 10, l)
}

func drawShelf(img *image.RGBA, c, d color.RGBA) {
	// две полки
	fillRoundRect(img, 58, 118, 242, 140, 5, d)
	fillRoundRect(img, 58, 178, 242, 200, 5, d)
	// кронштейны (L)
	thickLine(img, 70, 140, 70, 168, 6, c)
	thickLine(img, 70, 168, 96, 168, 6, c)
	thickLine(img, 230, 140, 230, 168, 6, c)
	thickLine(img, 204, 168, 230, 168, 6, c)
	thickLine(img, 70, 200, 70, 228, 6, c)
	thickLine(img, 70, 228, 96, 228, 6, c)
	thickLine(img, 230, 200, 230, 228, 6, c)
	thickLine(img, 204, 228, 230, 228, 6, c)
	// мелочь на полках
	fillRect(img, 96, 96, 116, 118, c)
	fillRect(img, 150, 88, 132, 118, shade(c, 12))
	fillRect(img, 178, 100, 200, 118, c)
}

func drawPouf(img *image.RGBA, c, d color.RGBA) {
	// изометрический куб: передняя грань
	fillPoly(img, [][2]int{{95, 150}, {205, 150}, {205, 250}, {95, 250}}, c)
	// верхняя грань (светлее)
	fillPoly(img, [][2]int{{95, 150}, {205, 150}, {235, 112}, {125, 112}}, shade(c, 18))
	// правая грань (темнее)
	fillPoly(img, [][2]int{{205, 150}, {235, 112}, {235, 212}, {205, 250}}, shade(c, -16))
	// контуры
	thickLine(img, 95, 150, 205, 150, 3, d)
	thickLine(img, 205, 150, 235, 112, 3, d)
	thickLine(img, 95, 150, 125, 112, 3, d)
	thickLine(img, 125, 112, 235, 112, 3, d)
	thickLine(img, 235, 112, 235, 212, 3, d)
	thickLine(img, 205, 250, 235, 212, 3, d)
	// пуговица-утапливание сверху
	fillCircle(img, 180, 124, 7, shade(c, -20))
}

func drawWardrobe(img *image.RGBA, c, d color.RGBA) {
	// карниз
	fillRoundRect(img, 72, 44, 228, 64, 5, d)
	// корпус
	fillRoundRect(img, 86, 64, 214, 262, 8, d)
	fillRoundRect(img, 94, 70, 206, 258, 6, c)
	// филёнки дверей
	fillRoundRect(img, 104, 86, 146, 244, 8, shade(c, -10))
	fillRoundRect(img, 154, 86, 196, 244, 8, shade(c, -10))
	// ручки
	fillRoundRect(img, 138, 150, 148, 172, 4, d)
	fillRoundRect(img, 152, 150, 162, 172, 4, d)
}

func drawDresser(img *image.RGBA, c, d color.RGBA) {
	fillRoundRect(img, 66, 92, 234, 250, 8, d)
	fillRoundRect(img, 74, 98, 226, 244, 6, c)
	// ящики
	for _, y := range []int{138, 172, 206} {
		thickLine(img, 80, y, 220, y, 3, shade(c, -14))
		fillRoundRect(img, 132, y-14, 168, y-2, 4, d) // ручка-скоба
	}
	// ножки
	thickLine(img, 86, 250, 82, 268, 8, d)
	thickLine(img, 214, 250, 218, 268, 8, d)
}

func drawNightstand(img *image.RGBA, c, d color.RGBA) {
	fillRoundRect(img, 92, 112, 208, 248, 8, d)
	fillRoundRect(img, 100, 118, 200, 242, 6, c)
	// ящик
	thickLine(img, 104, 178, 196, 178, 3, shade(c, -14))
	fillCircle(img, 150, 150, 8, d) // ручка
	// ножки
	thickLine(img, 108, 248, 104, 266, 8, d)
	thickLine(img, 192, 248, 196, 266, 8, d)
}

func drawBed(img *image.RGBA, c, d, l color.RGBA) {
	// изголовье
	fillRoundRect(img, 40, 70, 92, 250, 12, d)
	fillRoundRect(img, 46, 76, 86, 246, 8, c)
	// матрас
	fillRoundRect(img, 92, 150, 262, 230, 12, d)
	fillRoundRect(img, 98, 156, 256, 224, 8, c)
	// подушка
	fillRoundRect(img, 104, 150, 170, 188, 12, l)
	// линия одеяла
	thickLine(img, 98, 200, 256, 200, 4, shade(d, -8))
}

func drawBookshelf(img *image.RGBA, c, d color.RGBA) {
	// корпус
	fillRoundRect(img, 70, 46, 230, 262, 8, d)
	fillRoundRect(img, 80, 54, 220, 256, 4, shade(c, 22))
	// полки
	for _, y := range []int{110, 165, 220} {
		thickLine(img, 82, y, 218, y, 4, d)
	}
	// книги
	books := []struct{ x0, x1, y0, y1 int; col color.RGBA }{
		{92, 108, 74, 108, hsl(0, 0.6, 0.5)}, {110, 120, 66, 108, hsl(30, 0.6, 0.5)},
		{122, 140, 78, 108, hsl(210, 0.6, 0.5)}, {146, 158, 70, 108, hsl(140, 0.5, 0.45)},
		{92, 104, 130, 163, hsl(280, 0.5, 0.5)}, {106, 124, 124, 163, hsl(50, 0.6, 0.5)},
		{170, 186, 130, 163, hsl(0, 0.6, 0.5)}, {188, 200, 136, 163, hsl(200, 0.6, 0.45)},
		{92, 112, 186, 218, hsl(160, 0.5, 0.45)}, {114, 128, 180, 218, hsl(20, 0.6, 0.5)},
		{176, 192, 186, 218, hsl(330, 0.5, 0.5)},
	}
	for _, b := range books {
		fillRect(img, b.x0, b.y0, b.x1, b.y1, b.col)
	}
}

func drawBench(img *image.RGBA, c, d color.RGBA) {
	// сиденье
	fillRoundRect(img, 46, 148, 254, 182, 10, d)
	fillRoundRect(img, 52, 152, 248, 178, 7, c)
	// спинка: стойки + планка
	thickLine(img, 72, 108, 72, 150, 9, d)
	thickLine(img, 228, 108, 228, 150, 9, d)
	fillRoundRect(img, 50, 90, 250, 110, 8, d)
	fillRoundRect(img, 56, 94, 244, 106, 5, c)
	// ножки
	thickLine(img, 70, 182, 64, 246, 9, d)
	thickLine(img, 230, 182, 236, 246, 9, d)
}

func drawDiningSet(img *image.RGBA, c, d color.RGBA) {
	// стол по центру
	fillRoundRect(img, 96, 138, 204, 166, 6, d)
	fillRoundRect(img, 102, 142, 198, 162, 4, c)
	thickLine(img, 150, 166, 150, 244, 9, d)       // центральная ножка-опора
	thickLine(img, 120, 166, 130, 244, 6, shade(d, -6))
	thickLine(img, 180, 166, 170, 244, 6, shade(d, -6))
	// стул слева
	fillRoundRect(img, 40, 104, 70, 150, 6, d)
	fillRoundRect(img, 44, 150, 78, 168, 5, c)
	thickLine(img, 50, 168, 46, 210, 6, d)
	thickLine(img, 74, 168, 78, 210, 6, d)
	// стул справа (зеркально)
	fillRoundRect(img, 230, 104, 260, 150, 6, d)
	fillRoundRect(img, 222, 150, 256, 168, 5, c)
	thickLine(img, 226, 168, 222, 210, 6, d)
	thickLine(img, 250, 168, 254, 210, 6, d)
}

// ─── примитивы ──────────────────────────────────────────────────────────────

func setPx(img *image.RGBA, x, y int, c color.Color) {
	if x < 0 || y < 0 || x >= S || y >= S {
		return
	}
	img.Set(x, y, c)
}

func fillRect(img *image.RGBA, x0, y0, x1, y1 int, c color.Color) {
	if x1 < x0 {
		x0, x1 = x1, x0
	}
	if y1 < y0 {
		y0, y1 = y1, y0
	}
	draw.Draw(img, image.Rect(x0, y0, x1+1, y1+1), &image.Uniform{c}, image.Point{}, draw.Src)
}

func fillRoundRect(img *image.RGBA, x0, y0, x1, y1, r int, c color.Color) {
	if x1 < x0 {
		x0, x1 = x1, x0
	}
	if y1 < y0 {
		y0, y1 = y1, y0
	}
	w := x1 - x0
	h := y1 - y0
	if r < 0 {
		r = 0
	}
	if r*2 > w {
		r = w / 2
	}
	if r*2 > h {
		r = h / 2
	}
	// центральная область
	fillRect(img, x0+r, y0, x1-r, y1, c)
	fillRect(img, x0, y0+r, x1, y1-r, c)
	// углы
	fillCircle(img, x0+r, y0+r, r, c)
	fillCircle(img, x1-r, y0+r, r, c)
	fillCircle(img, x0+r, y1-r, r, c)
	fillCircle(img, x1-r, y1-r, r, c)
}

func fillCircle(img *image.RGBA, cx, cy, r int, c color.Color) {
	if r <= 0 {
		return
	}
	for y := -r; y <= r; y++ {
		for x := -r; x <= r; x++ {
			if x*x+y*y <= r*r {
				setPx(img, cx+x, cy+y, c)
			}
		}
	}
}

func fillEllipse(img *image.RGBA, cx, cy, rx, ry int, c color.Color) {
	if rx <= 0 || ry <= 0 {
		return
	}
	for y := -ry; y <= ry; y++ {
		for x := -rx; x <= rx; x++ {
			if float64(x*x)/float64(rx*rx)+float64(y*y)/float64(ry*ry) <= 1 {
				setPx(img, cx+x, cy+y, c)
			}
		}
	}
}

// thickLine — отрезок толщиной w со скруглёнными концами (штамп кружков вдоль).
func thickLine(img *image.RGBA, x0, y0, x1, y1, w int, c color.Color) {
	dx := float64(x1 - x0)
	dy := float64(y1 - y0)
	dist := math.Hypot(dx, dy)
	if dist == 0 {
		fillCircle(img, x0, y0, w/2, c)
		return
	}
	steps := int(dist) + 1
	for i := 0; i <= steps; i++ {
		t := float64(i) / float64(steps)
		fillCircle(img, int(float64(x0)+dx*t), int(float64(y0)+dy*t), w/2, c)
	}
}

func fillPoly(img *image.RGBA, pts [][2]int, c color.Color) {
	minY, maxY := 1<<30, -(1 << 30)
	for _, p := range pts {
		if p[1] < minY {
			minY = p[1]
		}
		if p[1] > maxY {
			maxY = p[1]
		}
	}
	n := len(pts)
	for y := minY; y <= maxY; y++ {
		var xs []int
		j := n - 1
		for i := 0; i < n; i++ {
			yi, yj := pts[i][1], pts[j][1]
			if (yi <= y && yj > y) || (yj <= y && yi > y) {
				xs = append(xs, pts[i][0]+(y-yi)*(pts[j][0]-pts[i][0])/(yj-yi))
			}
			j = i
		}
		sort.Ints(xs)
		for k := 0; k+1 < len(xs); k += 2 {
			fillRect(img, xs[k], y, xs[k+1], y, c)
		}
	}
}

// ─── цвет ──────────────────────────────────────────────────────────────────

func hsl(h, s, l float64) color.RGBA {
	h = math.Mod(h, 360)
	if h < 0 {
		h += 360
	}
	c := (1 - math.Abs(2*l-1)) * s
	x := c * (1 - math.Abs(math.Mod(h/60, 2)-1))
	m := l - c/2
	var r, g, b float64
	switch {
	case h < 60:
		r, g, b = c, x, 0
	case h < 120:
		r, g, b = x, c, 0
	case h < 180:
		r, g, b = 0, c, x
	case h < 240:
		r, g, b = 0, x, c
	case h < 300:
		r, g, b = x, 0, c
	default:
		r, g, b = c, 0, x
	}
	return color.RGBA{clamp8(r + m), clamp8(g + m), clamp8(b + m), 255}
}

// shade затемняет (dl<0) / осветляет (dl>0) цвет в единицах L (0..100).
func shade(c color.RGBA, dl int) color.RGBA {
	h, s, l := rgbToHsl(c)
	l += float64(dl) / 100
	if l < 0 {
		l = 0
	}
	if l > 1 {
		l = 1
	}
	return hsl(h, s, l)
}

func rgbToHsl(c color.RGBA) (float64, float64, float64) {
	r := float64(c.R) / 255
	g := float64(c.G) / 255
	b := float64(c.B) / 255
	max := math.Max(r, math.Max(g, b))
	min := math.Min(r, math.Min(g, b))
	l := (max + min) / 2
	var h, s float64
	if max != min {
		d := max - min
		if l > 0.5 {
			s = d / (2 - max - min)
		} else {
			s = d / (max + min)
		}
		switch max {
		case r:
			h = math.Mod((g-b)/d, 6)
		case g:
			h = (b-r)/d + 2
		case b:
			h = (r-g)/d + 4
		}
		h *= 60
		if h < 0 {
			h += 360
		}
	}
	return h, s, l
}

func clamp8(v float64) uint8 {
	if v < 0 {
		return 0
	}
	if v > 1 {
		return 255
	}
	return uint8(v * 255)
}
