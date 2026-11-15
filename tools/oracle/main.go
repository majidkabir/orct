// Command oracle prints, as JSON lines, what carbon-cost's own rate functions
// charge for a grid of trucks, times and payment means, on every table. The
// ORCT side (tools/check_oracle.py) prices the same cases from the converted
// datasets with the reference calculator; any difference is a conversion or
// calculator bug.
//
// It is built inside a carbon-cost checkout:
//
//	mkdir -p <carbon-cost>/cmd/orctoracle && cp tools/oracle/main.go <carbon-cost>/cmd/orctoracle/
//	(cd <carbon-cost> && go run ./cmd/orctoracle) > oracle.jsonl
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/majidkabir/carbon-cost/rates"
)

type truck struct {
	Mass, Axles, Motor, Euro, CO2 int
	Length                        float64
}

func (t truck) rates() rates.Truck {
	return rates.Truck{MaxMassKg: t.Mass, Axles: t.Axles, MotorAxles: t.Motor, Euro: t.Euro, CO2Class: t.CO2, LengthM: t.Length}
}

func grid(masses, axles, euros, co2s []int, lengths []float64) []truck {
	var out []truck
	for _, m := range masses {
		for _, a := range axles {
			for _, e := range euros {
				for _, c := range co2s {
					for _, l := range lengths {
						motor := a
						if a >= 4 {
							motor = 2
						}
						out = append(out, truck{m, a, motor, e, c, l})
					}
				}
			}
		}
	}
	return out
}

var (
	big   = grid([]int{3600, 7500, 12000, 18000, 26000, 40000, 44000}, []int{2, 3, 4, 5}, []int{3, 5, 6}, []int{1, 4, 5}, []float64{12})
	small = grid([]int{7500, 18000, 40000}, []int{2, 3, 5}, []int{5, 6}, []int{1, 5}, []float64{12, 18.75})
	out   = bufio.NewWriter(os.Stdout)
)

func emit(m map[string]any) {
	b, _ := json.Marshal(m)
	out.Write(b)
	out.WriteByte('\n')
}

func day(s string) time.Time {
	t, _ := time.Parse(time.DateOnly, s)
	return t
}

func main() {
	defer out.Flush()
	tables, err := rates.All()
	if err != nil {
		panic(err)
	}
	for _, tb := range tables {
		date := day(tb.ValidFrom)
		rowsCases(tb, date)
		pointCases(tb, date)
		groupCases(tb, date)
		congestionCases(tb, date)
		systemCases(tb)
		sectionCases(tb)
	}
	zones, err := rates.ZonesAll()
	if err != nil {
		panic(err)
	}
	for _, z := range zones {
		zoneCases(z)
	}
}

func rowsCases(tb rates.Table, date time.Time) {
	if len(tb.Rows) == 0 {
		return
	}
	keys := map[[2]string]bool{}
	for _, r := range tb.Rows {
		if r.Component == rates.EnvZoneSurcharge {
			continue
		}
		road := r.Road
		if r.Operator != "" {
			road = rates.Motorway
			parts := strings.Split(r.Operator, "|")
			for n := 1; n <= len(parts); n++ {
				keys[[2]string{road, strings.Join(parts[:n], "|")}] = true
			}
		}
		keys[[2]string{road, ""}] = true
	}
	var ks [][2]string
	for k := range keys {
		ks = append(ks, k)
	}
	sort.Slice(ks, func(i, j int) bool { return ks[i][0]+ks[i][1] < ks[j][0]+ks[j][1] })
	for _, t := range big {
		for _, k := range ks {
			rs, note, ok := tb.RatesFor(t.rates(), date, k[0], k[1])
			var lines []map[string]any
			for _, r := range rs {
				lines = append(lines, map[string]any{"component": r.Component, "area": r.Area, "per_km": r.PerKm})
			}
			emit(map[string]any{"kind": "rows", "file": tb.File, "truck": t, "road": k[0], "op": k[1],
				"date": tb.ValidFrom, "liable": ok, "exempt": note != "", "rates": lines})
		}
		if t.Mass >= tb.MinKg {
			if zr := tb.EnvZoneRate(t.rates()); zr != 0 {
				emit(map[string]any{"kind": "envzone", "file": tb.File, "truck": t, "date": tb.ValidFrom, "per_km": zr})
			}
		}
	}
}

// Times probed for points and systems: night, day and late evening.
var times = []string{"03:00", "12:00", "23:00"}

func pointCases(tb rates.Table, from time.Time) {
	for j, p := range tb.TollPoints {
		// A day in force, outside and (if the point has one) inside its high season.
		var days []time.Time
		d := from
		if p.ValidFrom != "" && day(p.ValidFrom).After(d) {
			d = day(p.ValidFrom)
		}
		var low, high time.Time
		for k := 0; k < 400 && (low.IsZero() || (p.HighSeason != nil && high.IsZero())); k++ {
			c := d.AddDate(0, 0, k)
			if !p.InForce(c) || (tb.ValidTo != "" && c.After(day(tb.ValidTo))) {
				continue
			}
			if p.Schedule != "" {
				if ok, _ := tb.Congestion.Taxed(c); !ok || tb.Congestion.High(c) {
					continue
				}
			}
			if p.HighSeason != nil && p.HighSeason.Has(c) {
				if high.IsZero() {
					high = c
				}
			} else if low.IsZero() {
				low = c
			}
		}
		for _, c := range []time.Time{low, high} {
			if !c.IsZero() {
				days = append(days, c)
			}
		}
		trucks := small
		if len(p.Classes) == 0 {
			trucks = small[:1]
		}
		etcs := []bool{false}
		for _, c := range p.Classes {
			if c.ETCRate > 0 || c.HighETCRate > 0 || c.NightETCRate > 0 {
				etcs = []bool{false, true}
			}
		}
		ts := []string{"12:00"}
		if len(p.NightHours) == 2 || len(p.FreeHours) == 2 {
			ts = times
		}
		if p.Schedule != "" {
			ts = []string{"05:59", "06:00", "06:29", "06:30", "07:00", "08:29", "08:30", "09:30", "15:00", "15:29", "15:30", "17:59", "18:00", "18:29", "18:30", "19:00"}
		}
		for _, c := range days {
			for _, t := range trucks {
				for _, etc := range etcs {
					for _, at := range ts {
						emit(map[string]any{"kind": "point", "file": tb.File, "j": j + 1, "truck": t, "etc": etc,
							"date": c.Format(time.DateOnly), "time": at, "amount": pointAmount(tb, p, t.rates(), etc, c, at)})
					}
				}
			}
		}
	}
}

// groupCases prices two passages of a group of toll points (the hour rule)
// as cost.go does: a passage that costs nothing is skipped, and after a paid
// passage the group's points are free for its minutes.
func groupCases(tb rates.Table, from time.Time) {
	type key struct{ g, mins int }
	groups := map[key][]int{}
	var keys []key
	for j, p := range tb.TollPoints {
		if p.Group == 0 || p.Schedule != "" {
			continue
		}
		mins := p.GroupMinutes
		if mins == 0 {
			mins = 60
		}
		k := key{p.Group, mins}
		if _, ok := groups[k]; !ok {
			keys = append(keys, k)
		}
		groups[k] = append(groups[k], j)
	}
	trucks := []truck{{7500, 2, 2, 6, 1, 12}, {40000, 5, 2, 6, 1, 12}}
	for _, k := range keys {
		days := []time.Time{from}
		seen := map[string]bool{from.Format(time.DateOnly): true}
		for _, j := range groups[k] {
			if v := tb.TollPoints[j].ValidFrom; v != "" && !seen[v] && day(v).After(from) && len(days) < 3 {
				seen[v] = true
				days = append(days, day(v))
			}
		}
		for _, d := range days {
			if tb.ValidTo != "" && d.After(day(tb.ValidTo)) {
				continue
			}
			for _, t := range trucks {
				var in, zero, paid []int
				for _, j := range groups[k] {
					p := tb.TollPoints[j]
					if !p.InForce(d) {
						continue
					}
					in = append(in, j)
					if a, _ := pointAmount(tb, p, t.rates(), false, d, "12:00").(float64); a == 0 {
						zero = append(zero, j)
					} else {
						paid = append(paid, j)
					}
				}
				var pairs [][2]int
				for n := 0; n+1 < len(in) && len(pairs) < 3; n++ {
					pairs = append(pairs, [2]int{in[n], in[n+1]})
				}
				if len(zero) > 0 && len(paid) > 0 {
					pairs = append(pairs, [2]int{zero[0], paid[0]})
				}
				for _, pr := range pairs {
					a, b := tb.TollPoints[pr[0]], tb.TollPoints[pr[1]]
					if a.Name == b.Name {
						continue // cost.go pays one station's booths once; that is map matching
					}
					for _, dm := range []int{k.mins - 1, k.mins, k.mins + 1} {
						hm := []string{"12:00", time.Date(2000, 1, 1, 12, dm, 0, 0, time.UTC).Format("15:04")}
						total, start, started := 0.0, 0, false
						for n, j := range pr {
							r, _ := pointAmount(tb, tb.TollPoints[j], t.rates(), false, d, hm[n]).(float64)
							m := 12*60 + n*dm
							if r == 0 || (started && m-start < k.mins) {
								continue
							}
							total, start, started = total+r, m, true
						}
						emit(map[string]any{"kind": "group", "file": tb.File, "truck": t, "date": d.Format(time.DateOnly),
							"passes": [][2]any{{pr[0] + 1, hm[0]}, {pr[1] + 1, hm[1]}}, "amount": total})
					}
				}
			}
		}
	}
}

// congestionCases prices one passage every day to 2035 (the tax's days and
// seasons) and, on a few days, passages one after another (the multi-pass
// window and the day cap), as cost.go's toll point loop does.
func congestionCases(tb rates.Table, from time.Time) {
	c := tb.Congestion
	if c == nil {
		return
	}
	var sched []int
	for j, p := range tb.TollPoints {
		if p.Schedule != "" && (len(sched) == 0 || tb.TollPoints[sched[0]].Name != p.Name) && len(sched) < 2 {
			sched = append(sched, j)
		}
	}
	if len(sched) < 2 {
		return
	}
	a, b := sched[0], sched[1]
	end := day("2035-12-31")
	if tb.ValidTo != "" && day(tb.ValidTo).Before(end) {
		end = day(tb.ValidTo)
	}
	var lowDay, highDay, freeDay time.Time
	for d := from; !d.After(end); d = d.AddDate(0, 0, 1) {
		emit(map[string]any{"kind": "congestion", "file": tb.File, "date": d.Format(time.DateOnly),
			"passes": [][2]any{{a + 1, "07:15"}}, "amount": congestionAmount(tb, d, [][2]any{{a, "07:15"}})})
		taxed, _ := c.Taxed(d)
		switch {
		case taxed && c.High(d) && highDay.IsZero():
			highDay = d
		case taxed && !c.High(d) && lowDay.IsZero():
			lowDay = d
		case !taxed && d.Weekday() != time.Saturday && d.Weekday() != time.Sunday && freeDay.IsZero():
			freeDay = d
		}
	}
	seqs := [][][2]any{
		{{a, "07:00"}, {b, "07:30"}}, {{a, "06:00"}, {b, "06:45"}}, {{a, "06:45"}, {b, "07:44"}}, {{a, "06:45"}, {b, "07:45"}},
		{{a, "05:59"}, {b, "06:30"}}, {{a, "18:29"}, {b, "18:30"}},
		{{a, "06:30"}, {b, "07:15"}, {a, "08:00"}, {b, "08:45"}, {a, "15:30"}, {b, "16:15"}, {a, "17:00"}, {b, "17:45"}},
	}
	for _, d := range []time.Time{lowDay, highDay, freeDay} {
		if d.IsZero() {
			continue
		}
		for _, sq := range seqs {
			var passes [][2]any
			for _, p := range sq {
				passes = append(passes, [2]any{p[0].(int) + 1, p[1]})
			}
			emit(map[string]any{"kind": "congestion", "file": tb.File, "date": d.Format(time.DateOnly),
				"passes": passes, "amount": congestionAmount(tb, d, sq)})
		}
	}
}

// congestionAmount follows cost.go's loop for timed passages of congestion
// points on one day, in time order.
func congestionAmount(tb rates.Table, d time.Time, passes [][2]any) any {
	c := tb.Congestion
	total, dayTotal := 0.0, 0.0
	var window time.Time
	windowAmt := 0.0
	for _, p := range passes {
		hm := p[1].(string)
		h, _ := time.Parse("15:04", hm)
		at := d.Add(time.Duration(h.Hour())*time.Hour + time.Duration(h.Minute())*time.Minute)
		if taxed, _ := c.Taxed(at); !taxed {
			continue
		}
		amt, err := c.Amount(tb.TollPoints[p[0].(int)].Schedule, at, hm)
		if err != nil {
			return fmt.Sprint(err)
		}
		if amt == 0 {
			continue
		}
		if c.MultiPassMinutes > 0 && !window.IsZero() && at.Sub(window) < time.Duration(c.MultiPassMinutes)*time.Minute {
			if amt <= windowAmt {
				continue
			}
			amt, windowAmt = amt-windowAmt, amt
		} else if c.MultiPassMinutes > 0 {
			window, windowAmt = at, amt
		}
		if dayCap := c.Cap(at); dayCap > 0 && dayTotal+amt > dayCap {
			amt = dayCap - dayTotal
			if amt <= 0 {
				continue
			}
		}
		dayTotal += amt
		total += amt
	}
	return total
}

// pointAmount follows cost.go's toll point loop for one timed passage.
func pointAmount(tb rates.Table, p rates.TollPoint, t rates.Truck, etc bool, d time.Time, at string) any {
	if t.MaxMassKg < tb.MinKg {
		return 0.0
	}
	if p.Schedule != "" {
		a, err := tb.Congestion.Amount(p.Schedule, d, at)
		if err != nil {
			return fmt.Sprint(err)
		}
		return a
	}
	if len(p.FreeHours) == 2 {
		if free, _ := rates.Within(at, p.FreeHours[0], p.FreeHours[1]); free {
			return 0.0
		}
	}
	rate, ok := p.PriceOn(t, etc, d)
	if !ok || rate == 0 {
		return 0.0
	}
	if len(p.NightHours) == 2 {
		if nr, has := p.NightPrice(t, etc); has && nr != rate {
			if night, _ := rates.Within(at, p.NightHours[0], p.NightHours[1]); night {
				rate = nr
			}
		}
	}
	return rate
}

func systemCases(tb rates.Table) {
	for i, s := range tb.Closed {
		var keys []string
		for k := range s.Prices {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		step := 1
		if len(keys) > 25 {
			step = len(keys) / 25
		}
		var pairs [][2]string
		for n := 0; n < len(keys); n += step {
			a, b, _ := strings.Cut(keys[n], "|")
			pairs = append(pairs, [2]string{a, b}, [2]string{b, a})
		}
		ts := []string{"12:00"}
		if len(s.NightHours) == 2 || len(s.FreeHours) == 2 {
			ts = times
		}
		etcs := []bool{false}
		if s.ETCPrices != nil || len(s.Discounts) > 0 {
			etcs = []bool{false, true}
		}
		for _, pr := range pairs {
			for _, t := range small {
				for _, etc := range etcs {
					for _, at := range ts {
						emit(map[string]any{"kind": "system", "file": tb.File, "i": i + 1, "entry": pr[0], "exit": pr[1],
							"truck": t, "etc": etc, "date": tb.ValidFrom, "time": at, "amount": systemAmount(tb, s, t.rates(), etc, at, pr)})
					}
				}
			}
		}
	}
}

// systemAmount follows cost.go's closed-system pricing for one trip entering at `at`; nil = no price.
func systemAmount(tb rates.Table, s rates.TollSystem, t rates.Truck, etc bool, at string, pr [2]string) any {
	if t.MaxMassKg < tb.MinKg {
		return 0.0
	}
	if len(s.FreeHours) == 2 {
		if free, _ := rates.Within(at, s.FreeHours[0], s.FreeHours[1]); free {
			return 0.0
		}
	}
	g := s.GroupOf(t)
	p, ok := s.Price(pr[0], pr[1], g, etc)
	if len(s.NightHours) == 2 {
		if night, _ := rates.Within(at, s.NightHours[0], s.NightHours[1]); night {
			n := s
			n.Prices, n.ETCPrices = s.NightPrices, nil
			p, ok = n.Price(pr[0], pr[1], g, false)
		}
	}
	if !ok {
		return nil
	}
	var pct float64
	for _, d := range s.Discounts {
		if d.Applies(t, etc) {
			pct += d.Percent
		}
	}
	if pct > 0 {
		p = math.Round(p*(1-pct/100)*100) / 100 // cost.go round2
	}
	return p
}

func sectionCases(tb rates.Table) {
	if tb.Sections == nil {
		return
	}
	for _, s := range tb.Sections.List {
		for _, t := range small {
			for _, night := range []bool{false, true} {
				emit(map[string]any{"kind": "section", "file": tb.File, "id": s.ID, "truck": t, "night": night,
					"date": tb.ValidFrom, "amount": s.Amount(t.rates(), night)})
			}
			for _, pk := range tb.Sections.PerKm {
				r, ok := pk.Rate(t.rates(), s)
				var v any
				if ok && s.Km > 0 {
					v = r * s.Km
				}
				emit(map[string]any{"kind": "section_km", "file": tb.File, "id": s.ID, "component": pk.Component,
					"truck": t, "date": tb.ValidFrom, "amount": v})
			}
		}
	}
}

func zoneCases(z rates.Zone) {
	from := day(z.ValidFrom)
	var probes []time.Time
	for k := 0; k < 370; k++ {
		d := from.AddDate(0, 0, k)
		if z.ValidTo != "" && d.After(day(z.ValidTo)) {
			break
		}
		if k < 8 || d.Format("01-02") == "12-25" || d.Format("01-02") == "01-01" {
			for _, hm := range []string{"06:59", "07:00", "12:00", "17:59", "18:00", "18:01", "23:00"} {
				h, _ := time.Parse("15:04", hm)
				probes = append(probes, d.Add(time.Duration(h.Hour())*time.Hour+time.Duration(h.Minute())*time.Minute))
			}
		}
	}
	for _, at := range probes {
		for _, euro := range []int{0, 3, 4, 5, 6} {
			for _, mass := range []int{3000, 12000, 40000} {
				amount := 0.0
				exempt := z.ExemptEuro > 0 && euro >= z.ExemptEuro // as cost.go
				if mass >= z.MinKg && !exempt && z.Charging(at) {
					amount = z.ChargeFor(euro)
				}
				emit(map[string]any{"kind": "zone", "file": z.File, "euro": euro, "mass": mass,
					"date": at.Format(time.DateOnly), "time": at.Format("15:04"), "amount": amount})
			}
		}
	}
}
