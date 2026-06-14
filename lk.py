#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lkdata")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

FILES = {
    "windows": os.path.join(DATA_DIR, "windows.json"),
    "applicants": os.path.join(DATA_DIR, "applicants.json"),
    "sensitive": os.path.join(DATA_DIR, "sensitive.json"),
    "contacts": os.path.join(DATA_DIR, "contacts.json"),
    "confirmations": os.path.join(DATA_DIR, "confirmations.json"),
    "abnormals": os.path.join(DATA_DIR, "abnormals.json"),
    "nofly": os.path.join(DATA_DIR, "nofly.json"),
    "duty": os.path.join(DATA_DIR, "duty.json"),
    "reviews": os.path.join(DATA_DIR, "reviews.json"),
    "stats": os.path.join(DATA_DIR, "stats.json"),
}

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

def _load(key):
    path = FILES[key]
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(key, data):
    _ensure_dirs()
    path = FILES[key]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(items):
    if not items:
        return 1
    return max(i.get("id", 0) for i in items) + 1

def _today():
    return date.today().isoformat()

def _now():
    return datetime.now().strftime("%H:%M")

def _now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def _find_window(windows, wid, only_active=False):
    for w in windows:
        if w["id"] == wid:
            if only_active and w["status"] != "active":
                return None
            return w
    return None

# ─── 录入飞行窗口 ───
def cmd_add_window(args):
    items = _load("windows")
    entry = {
        "id": _next_id(items),
        "date": args.date or _today(),
        "start": args.start,
        "end": args.end,
        "alt_min": args.alt_min,
        "alt_max": args.alt_max,
        "township": args.township,
        "applicant_id": args.applicant,
        "purpose": args.purpose or "",
        "status": "active",
    }
    items.append(entry)
    _save("windows", items)
    print(f"✔ 飞行窗口 #{entry['id']} 已录入  {entry['date']} {entry['start']}-{entry['end']}  "
          f"高度{entry['alt_min']}-{entry['alt_max']}m  {entry['township']}")

# ─── 登记申请方 ───
def cmd_add_applicant(args):
    items = _load("applicants")
    entry = {
        "id": _next_id(items),
        "name": args.name,
        "org": args.org or "",
        "phone": args.phone or "",
        "atype": args.atype or "personal",
    }
    items.append(entry)
    _save("applicants", items)
    print(f"✔ 申请方 #{entry['id']} 已登记  {entry['name']} ({entry['org']})")

# ─── 标注学校医院活动点 ───
def cmd_mark_sensitive(args):
    items = _load("sensitive")
    entry = {
        "id": _next_id(items),
        "name": args.name,
        "stype": args.stype,
        "township": args.township,
        "radius": args.radius or 500,
        "note": args.note or "",
    }
    items.append(entry)
    _save("sensitive", items)
    print(f"✔ 敏感点 #{entry['id']} 已标注  {entry['name']} [{entry['stype']}] {entry['township']} 半径{entry['radius']}m")

# ─── 添加临时禁飞 ───
def cmd_add_nofly(args):
    items = _load("nofly")
    entry = {
        "id": _next_id(items),
        "township": args.township,
        "reason": args.reason,
        "start": args.start or _now(),
        "end": args.end or "23:59",
        "date": args.date or _today(),
    }
    items.append(entry)
    _save("nofly", items)
    print(f"✔ 临时禁飞 #{entry['id']} 已添加  {entry['township']} {entry['date']} {entry['start']}-{entry['end']}  原因:{entry['reason']}")

# ─── 检查高度重叠 ───
def cmd_check_altitude(args):
    windows = _load("windows")
    check_date = args.date or _today()
    day_windows = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    if not day_windows:
        print(f"✔ {check_date} 无活跃飞行窗口，无高度重叠")
        return
    day_windows.sort(key=lambda w: (w["township"], w["start"]))
    conflicts = []
    for i in range(len(day_windows)):
        for j in range(i + 1, len(day_windows)):
            a, b = day_windows[i], day_windows[j]
            if a["township"] != b["township"]:
                continue
            if a["alt_max"] <= b["alt_min"] or b["alt_max"] <= a["alt_min"]:
                continue
            time_overlap = not (a["end"] <= b["start"] or b["end"] <= a["start"])
            if time_overlap:
                conflicts.append((a, b))
    if not conflicts:
        print(f"✔ {check_date} 无高度重叠冲突")
    else:
        print(f"⚠ {check_date} 发现 {len(conflicts)} 组高度重叠：")
        for a, b in conflicts:
            print(f"  窗口#{a['id']}({a['start']}-{a['end']} {a['alt_min']}-{a['alt_max']}m) ↔ "
                  f"窗口#{b['id']}({b['start']}-{b['end']} {b['alt_min']}-{b['alt_max']}m)  乡镇:{a['township']}")

# ─── 提示临时禁飞 ───
def cmd_show_nofly(args):
    items = _load("nofly")
    check_date = args.date or _today()
    now_time = _now()
    active = [n for n in items if n["date"] == check_date and n["end"] >= now_time]
    if not active:
        print(f"✔ {check_date} 当前无临时禁飞")
    else:
        print(f"⚠ {check_date} 临时禁飞区域：")
        for n in active:
            print(f"  {n['township']}  {n['start']}-{n['end']}  原因:{n['reason']}")

# ─── 登记联络人 ───
def cmd_add_contact(args):
    items = _load("contacts")
    entry = {
        "id": _next_id(items),
        "name": args.name,
        "role": args.role or "",
        "phone": args.phone or "",
        "township": args.township or "",
    }
    items.append(entry)
    _save("contacts", items)
    print(f"✔ 联络人 #{entry['id']} 已登记  {entry['name']} {entry['role']} {entry['phone']}")

# ─── 记录放飞前确认 ───
def cmd_confirm(args):
    windows = _load("windows")
    wid = args.window_id
    target = _find_window(windows, wid, only_active=True)
    if not target:
        print(f"✘ 未找到活跃窗口 #{wid}")
        return
    biz_date = args.biz_date or target["date"]
    items = _load("confirmations")
    existing = next((c for c in items if c["window_id"] == wid and c["date"] == biz_date), None)
    if existing:
        existing["confirmer"] = args.confirmer
        existing["time"] = _now()
        existing["notes"] = args.notes or existing.get("notes", "")
        existing["created_at"] = _now_ts()
        tag = "（补录更新）" if biz_date != _today() else ""
        _save("confirmations", items)
        print(f"✔ 窗口#{wid} 放飞前确认已更新{tag}  业务日:{biz_date}  确认人:{args.confirmer}  {_now()}")
        return
    entry = {
        "id": _next_id(items),
        "window_id": wid,
        "confirmer": args.confirmer,
        "time": _now(),
        "date": biz_date,
        "created_at": _now_ts(),
        "notes": args.notes or "",
    }
    items.append(entry)
    _save("confirmations", items)
    tag = "（补录）" if biz_date != _today() else ""
    print(f"✔ 窗口#{wid} 放飞前确认已记录{tag}  业务日:{biz_date}  确认人:{entry['confirmer']}  {entry['time']}")

# ─── 补记异常返航 ───
def cmd_abnormal(args):
    windows = _load("windows")
    wid = args.window_id
    target = _find_window(windows, wid)
    if not target:
        print(f"✘ 未找到窗口 #{wid}")
        return
    biz_date = args.biz_date or target["date"]
    items = _load("abnormals")
    existing = next((a for a in items if a["window_id"] == wid and a["date"] == biz_date), None)
    if existing:
        existing["return_time"] = args.time or existing.get("return_time", _now())
        existing["reason"] = args.reason
        existing["notes"] = args.notes or existing.get("notes", "")
        existing["created_at"] = _now_ts()
        tag = "（补录更新）" if biz_date != _today() else ""
        _save("abnormals", items)
        print(f"✔ 窗口#{wid} 异常返航已更新{tag}  业务日:{biz_date}  {existing['return_time']}  原因:{args.reason}")
        return
    entry = {
        "id": _next_id(items),
        "window_id": wid,
        "return_time": args.time or _now(),
        "date": biz_date,
        "created_at": _now_ts(),
        "reason": args.reason,
        "notes": args.notes or "",
    }
    items.append(entry)
    _save("abnormals", items)
    tag = "（补录）" if biz_date != _today() else ""
    print(f"✔ 窗口#{wid} 异常返航已补记{tag}  业务日:{biz_date}  {entry['return_time']}  原因:{entry['reason']}")

# ─── 输出口头播报稿 ───
def cmd_broadcast(args):
    windows = _load("windows")
    nofly = _load("nofly")
    sensitive = _load("sensitive")
    check_date = args.date or _today()
    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    day_nf = [n for n in nofly if n["date"] == check_date]
    applicants = {a["id"]: a for a in _load("applicants")}

    lines = [f"【低空飞行服务点口头播报稿 — {check_date}】", ""]

    if day_w:
        lines.append("今日飞行窗口：")
        for w in day_w:
            ap = applicants.get(w["applicant_id"], {})
            ap_name = ap.get("name", "未知")
            lines.append(f"  · {w['start']}-{w['end']}，{w['township']}，高度{w['alt_min']}-{w['alt_max']}m，"
                         f"申请方：{ap_name}，用途：{w.get('purpose','未注明')}")
    else:
        lines.append("今日暂无飞行窗口。")

    lines.append("")
    if day_nf:
        lines.append("临时禁飞提醒：")
        for n in day_nf:
            lines.append(f"  · {n['township']} {n['start']}-{n['end']}，原因：{n['reason']}")
    else:
        lines.append("无临时禁飞。")

    lines.append("")
    day_sensitive = [s for s in sensitive if any(w["township"] == s["township"] for w in day_w)]
    if day_sensitive:
        lines.append("涉及敏感区域：")
        for s in day_sensitive:
            lines.append(f"  · {s['name']}（{s['stype']}）{s['township']} 半径{s['radius']}m")
    else:
        lines.append("无敏感区域交叉。")

    lines.append("")
    lines.append("请各相关方注意安全，严格遵守飞行窗口时间与高度限制。")
    print("\n".join(lines))

# ─── 生成短信模板 ───
def cmd_sms(args):
    windows = _load("windows")
    nofly = _load("nofly")
    check_date = args.date or _today()
    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    day_nf = [n for n in nofly if n["date"] == check_date]
    applicants = {a["id"]: a for a in _load("applicants")}

    if not day_w and not day_nf:
        print(f"【{check_date} 低空飞行服务点通知】今日无飞行计划，无禁飞通知。")
        return

    parts = [f"【{check_date} 低空飞行服务点通知】"]
    if day_w:
        w_descs = []
        for w in day_w:
            ap = applicants.get(w["applicant_id"], {})
            w_descs.append(f"{w['start']}-{w['end']} {w['township']} {w['alt_min']}-{w['alt_max']}m")
        parts.append("飞行窗口：" + "；".join(w_descs) + "。")
    if day_nf:
        nf_descs = [f"{n['township']}({n['reason']})" for n in day_nf]
        parts.append("临时禁飞：" + "；".join(nf_descs) + "。")
    parts.append("请注意安全。")
    print("".join(parts))

# ─── 快速查询当天占用 ───
def cmd_today(args):
    windows = _load("windows")
    confirmations = _load("confirmations")
    reviews = _load("reviews")
    abnormals = _load("abnormals")
    check_date = args.date or _today()
    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    if not day_w:
        print(f"✔ {check_date} 无活跃飞行窗口")
        return
    confirmed_ids = {c["window_id"] for c in confirmations if c["date"] == check_date}
    reviewed_ids = {r["window_id"] for r in reviews if r["date"] == check_date}
    abnormal_ids = {a["window_id"] for a in abnormals if a["date"] == check_date}
    applicants = {a["id"]: a for a in _load("applicants")}
    print(f"📋 {check_date} 占用情况（{len(day_w)}个窗口）：")
    for w in sorted(day_w, key=lambda x: x["start"]):
        ap = applicants.get(w["applicant_id"], {})
        status_bits = []
        status_bits.append("确认" if w["id"] in confirmed_ids else "未确认")
        status_bits.append("复核" if w["id"] in reviewed_ids else "未复核")
        if w["id"] in abnormal_ids:
            status_bits.append("异常返航")
        status_str = " | ".join(status_bits)
        print(f"  #{w['id']}  {w['start']}-{w['end']}  {w['township']}  "
              f"{w['alt_min']}-{w['alt_max']}m  申请方:{ap.get('name','?')}  用途:{w.get('purpose','')}")
        print(f"         状态: {status_str}")

# ─── 按乡镇筛冲突 ───
def cmd_conflict(args):
    windows = _load("windows")
    nofly = _load("nofly")
    check_date = args.date or _today()
    township = args.township
    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active" and w["township"] == township]
    day_nf = [n for n in nofly if n["date"] == check_date and n["township"] == township]

    print(f"🔍 {check_date} {township} 冲突筛查：")
    found = False

    for n in day_nf:
        for w in day_w:
            if not (w["end"] <= n["start"] or n["end"] <= w["start"]):
                print(f"  ⚠ 窗口#{w['id']}({w['start']}-{w['end']}) 与禁飞{n['start']}-{n['end']} 冲突  原因:{n['reason']}")
                found = True

    day_w.sort(key=lambda w: w["start"])
    for i in range(len(day_w)):
        for j in range(i + 1, len(day_w)):
            a, b = day_w[i], day_w[j]
            if not (a["end"] <= b["start"] or b["end"] <= a["start"]):
                if a["alt_max"] > b["alt_min"] and b["alt_max"] > a["alt_min"]:
                    print(f"  ⚠ 窗口#{a['id']}({a['start']}-{a['end']} {a['alt_min']}-{a['alt_max']}m) ↔ "
                          f"窗口#{b['id']}({b['start']}-{b['end']} {b['alt_min']}-{b['alt_max']}m) 时间+高度重叠")
                    found = True

    if not found:
        print(f"  ✔ 无冲突")

# ─── 设置值班表 ───
def cmd_set_duty(args):
    items = _load("duty")
    check_date = args.date or _today()
    existing = [d for d in items if d["date"] != check_date]
    entry = {
        "id": _next_id(items),
        "date": check_date,
        "coordinator": args.name,
        "phone": args.phone or "",
    }
    existing.append(entry)
    _save("duty", existing)
    print(f"✔ 值班已设置  {check_date}  {args.name} {args.phone or ''}")

# ─── 打印简版值班表 ───
def cmd_duty(args):
    items = _load("duty")
    if not items:
        print("暂无值班记录")
        return
    items.sort(key=lambda d: d["date"], reverse=True)
    print("📋 简版值班表：")
    print(f"  {'日期':<12} {'协调员':<10} {'电话':<15}")
    print("  " + "-" * 37)
    for d in items[:14]:
        print(f"  {d['date']:<12} {d['coordinator']:<10} {d.get('phone',''):<15}")

# ─── 归档已结束任务 ───
def cmd_archive(args):
    windows = _load("windows")
    today = _today()
    to_archive = [w for w in windows if w["date"] < today and w["status"] == "active"]
    if not to_archive:
        print("✔ 无需归档（无已结束的活跃窗口）")
        return
    for w in to_archive:
        w["status"] = "archived"
    _save("windows", windows)
    if to_archive:
        archive_path = os.path.join(ARCHIVE_DIR, f"archive_{today}.json")
        existing_archive = []
        if os.path.exists(archive_path):
            with open(archive_path, "r", encoding="utf-8") as f:
                existing_archive = json.load(f)
        existing_archive.extend(to_archive)
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(existing_archive, f, ensure_ascii=False, indent=2)
    print(f"✔ 已归档 {len(to_archive)} 个已结束窗口 → {archive_path}")

# ─── 累计连续零漏报天数 ───
def cmd_streak(args):
    stats = _load("stats")
    if not stats:
        stats = {"streak": 0, "last_miss_date": None, "last_streak_date": None}
    streak = stats.get("streak", 0)
    last_miss = stats.get("last_miss_date")
    last_streak = stats.get("last_streak_date")
    if streak > 0:
        print(f"🔥 连续零漏报天数：{streak} 天")
        if last_streak == _today():
            print(f"  今日已计入")
    else:
        print("尚无连续零漏报记录")
    if last_miss:
        print(f"  上次漏报日期：{last_miss}")

def _record_streak(for_date=None):
    stats = _load("stats")
    if not stats:
        stats = {"streak": 0, "last_miss_date": None, "last_streak_date": None}
    today = for_date or _today()
    if stats.get("last_streak_date") == today:
        return False
    stats["streak"] = stats.get("streak", 0) + 1
    stats["last_streak_date"] = today
    _save("stats", stats)
    return True

def _break_streak(reason="", for_date=None):
    stats = _load("stats")
    if not stats:
        stats = {"streak": 0, "last_miss_date": None, "last_streak_date": None}
    today = for_date or _today()
    if stats.get("streak", 0) > 0:
        print(f"⚠ 连续零漏报中断（之前连续{stats['streak']}天）原因：{reason}")
    stats["streak"] = 0
    stats["last_miss_date"] = today
    stats["last_streak_date"] = None
    _save("stats", stats)

# ─── 给按时复核加星 ───
def cmd_star(args):
    windows = _load("windows")
    wid = args.window_id
    target = _find_window(windows, wid)
    if not target:
        print(f"✘ 未找到窗口 #{wid}")
        return
    biz_date = args.biz_date or target["date"]
    items = _load("reviews")
    existing = next((r for r in items if r["window_id"] == wid and r["date"] == biz_date), None)
    if existing:
        existing["reviewer"] = args.reviewer
        existing["time"] = _now()
        existing["created_at"] = _now_ts()
        _save("reviews", items)
        tag = "（补录更新）" if biz_date != _today() else ""
        print(f"⭐ 窗口#{wid} 复核已更新{tag}  业务日:{biz_date}  复核人:{args.reviewer}  不重复计数")
        return
    entry = {
        "id": _next_id(items),
        "window_id": wid,
        "reviewer": args.reviewer,
        "on_time": True,
        "date": biz_date,
        "created_at": _now_ts(),
        "time": _now(),
    }
    items.append(entry)
    _save("reviews", items)
    streak_added = False
    if biz_date == _today():
        streak_added = _record_streak()
    tag = "（补录）" if biz_date != _today() else ""
    if biz_date == _today() and streak_added:
        print(f"⭐ 窗口#{wid} 按时复核加星{tag}  业务日:{biz_date}  复核人:{args.reviewer}  今日连续零漏报已累计")
    else:
        print(f"⭐ 窗口#{wid} 按时复核加星{tag}  业务日:{biz_date}  复核人:{args.reviewer}")

# ─── 补录判断工具 ───
def _is_backfilled(record, window):
    created = record.get("created_at", "")
    if not created:
        return False
    biz_date = record.get("date", "")
    try:
        created_day = created.split(" ")[0]
        if created_day > biz_date:
            return True
        if created_day == biz_date:
            created_time = created.split(" ")[1]
            if created_time > window["end"]:
                return True
    except (IndexError, ValueError):
        pass
    return False

# ─── 补分关卡（增强：区分即时完成 / 补录完成 / 遗漏） ───
def cmd_gaps(args):
    windows = _load("windows")
    confirmations = _load("confirmations")
    reviews = _load("reviews")
    abnormals = _load("abnormals")
    check_date = args.date or _today()
    now = _now()

    conf_by_win = {c["window_id"]: c for c in confirmations if c["date"] == check_date}
    rev_by_win = {r["window_id"]: r for r in reviews if r["date"] == check_date}
    abn_by_win = {a["window_id"]: a for a in abnormals if a["date"] == check_date}

    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    if not day_w:
        print(f"✔ {check_date} 无活跃飞行窗口")
        return

    done_prompt = []
    done_backfill = []
    gaps = []

    def classify(record, window, check_type, desc_done, desc_miss):
        rid = window["id"]
        if rid in record:
            rec = record[rid]
            if _is_backfilled(rec, window):
                done_backfill.append(f"[补录] 窗口#{rid} {desc_done}  补录于{rec.get('created_at','?')}")
            else:
                done_prompt.append(f"[正常] 窗口#{rid} {desc_done}")
        else:
            is_past = (check_date < _today()) or (check_date == _today() and window["end"] <= now)
            if check_type in ("确认", "复核") and not is_past:
                pass
            elif check_type == "异常返航漏记":
                if rid in conf_by_win and rid not in rev_by_win and is_past:
                    gaps.append({"type": "异常返航漏记", "detail": f"窗口#{rid} 已结束但无异常返航记录，请核实是否需补记"})
            else:
                gaps.append({"type": desc_miss, "detail": f"窗口#{rid} {desc_miss}"})

    for w in day_w:
        classify(conf_by_win, w, "确认", "放飞前已确认", "放飞前未确认")
    for w in day_w:
        classify(rev_by_win, w, "复核", "已按时复核", "尚未按时复核")
    for w in day_w:
        classify(abn_by_win, w, "异常返航漏记", "有异常返航记录", None)

    nofly = _load("nofly")
    day_nf = [n for n in nofly if n["date"] == check_date]
    nf_conflicts = []
    for n in day_nf:
        conflict_windows = [w for w in day_w if w["township"] == n["township"]
                           and not (w["end"] <= n["start"] or n["end"] <= w["start"])]
        for w in conflict_windows:
            nf_conflicts.append({"window_id": w["id"], "reason": n["reason"],
                                "detail": f"窗口#{w['id']} 与禁飞冲突未处理（原因:{n['reason']}）"})
    # 禁飞冲突统一归为遗漏
    for nc in nf_conflicts:
        gaps.append({"type": "禁飞冲突", "detail": nc["detail"]})

    print(f"📊 {check_date} 补分关卡总览")
    if done_prompt:
        print(f"\n✅ 正常完成（{len(done_prompt)}项）：")
        for line in done_prompt:
            print(f"  {line}")
    if done_backfill:
        print(f"\n🔧 补录完成（{len(done_backfill)}项）：")
        for line in done_backfill:
            print(f"  {line}")
    if gaps:
        print(f"\n🎯 仍待补（{len(gaps)}项）：")
        for i, g in enumerate(gaps, 1):
            print(f"  {i}. [{g['type']}] {g['detail']}")
    if not gaps:
        print(f"\n✔ {check_date} 全部关卡已通过，无遗留问题！")
        if check_date == _today():
            _record_streak()
    return {
        "done_prompt": len(done_prompt),
        "done_backfill": len(done_backfill),
        "gaps": len(gaps),
        "gaps_detail": gaps,
    }

# ─── 日结命令 ───
def cmd_daily_summary(args):
    check_date = args.date or _today()
    windows = _load("windows")
    confirmations = _load("confirmations")
    reviews = _load("reviews")
    abnormals = _load("abnormals")
    nofly = _load("nofly")
    duty = _load("duty")

    day_w = [w for w in windows if w["date"] == check_date and w["status"] == "active"]
    total_w = len(day_w)
    conf_list = [c for c in confirmations if c["date"] == check_date]
    rev_list = [r for r in reviews if r["date"] == check_date]
    abn_list = [a for a in abnormals if a["date"] == check_date]
    conf_ids = {c["window_id"] for c in conf_list}
    rev_ids = {r["window_id"] for r in rev_list}
    abn_ids = {a["window_id"] for a in abn_list}

    nf_conflicts = 0
    day_nf = [n for n in nofly if n["date"] == check_date]
    for n in day_nf:
        for w in day_w:
            if w["township"] == n["township"] and not (w["end"] <= n["start"] or n["end"] <= w["start"]):
                nf_conflicts += 1

    duty_today = next((d for d in duty if d["date"] == check_date), None)

    print(f"═══════════════════════════════════════════")
    print(f"  低空飞行服务点  日结报告  {check_date}")
    print(f"═══════════════════════════════════════════")
    if duty_today:
        print(f"值班协调员：{duty_today['coordinator']}  {duty_today.get('phone','')}")
    print(f"")
    print(f"飞行窗口     ：{total_w} 个")
    print(f"放飞前已确认 ：{len(conf_ids)} / {total_w}")
    print(f"按时已复核   ：{len(rev_ids)} / {total_w}")
    print(f"异常返航记录 ：{len(abn_ids)} 条")
    print(f"禁飞冲突     ：{nf_conflicts} 组")
    print(f"")

    result = cmd_gaps(args)
    gaps_count = result["gaps"] if result else 0

    print(f"")
    print(f"───────────────────────────────────────────")
    if gaps_count == 0:
        print(f"🏆 日结结论：当天收工干净，达标！")
        if check_date == _today():
            added = _record_streak()
            stats = _load("stats")
            print(f"🔥 当前连续零漏报：{stats.get('streak',0)} 天" + ("（今日已计入）" if not added else ""))
        else:
            print(f"（历史日结，不触发 streak）")
    else:
        print(f"⚠  日结结论：仍有 {gaps_count} 项遗漏待补")
        if check_date == _today():
            print(f"  今日暂未达标，请处理完遗漏项后再跑 daily-summary 确认")
    print(f"═══════════════════════════════════════════")


# ─── 列出申请方 ───
def cmd_list_applicants(args):
    items = _load("applicants")
    if not items:
        print("暂无申请方")
        return
    print(f"📋 申请方列表（{len(items)}条）：")
    for a in items:
        print(f"  #{a['id']}  {a['name']}  机构:{a.get('org','')}  电话:{a.get('phone','')}  类型:{a.get('atype','')}")

# ─── 列出联络人 ───
def cmd_list_contacts(args):
    items = _load("contacts")
    if not items:
        print("暂无联络人")
        return
    print(f"📋 联络人列表（{len(items)}条）：")
    for c in items:
        print(f"  #{c['id']}  {c['name']}  角色:{c.get('role','')}  电话:{c.get('phone','')}  乡镇:{c.get('township','')}")

# ─── 列出敏感点 ───
def cmd_list_sensitive(args):
    items = _load("sensitive")
    if not items:
        print("暂无敏感点")
        return
    print(f"📋 敏感点列表（{len(items)}条）：")
    for s in items:
        print(f"  #{s['id']}  {s['name']}  类型:{s['stype']}  乡镇:{s['township']}  半径:{s['radius']}m")


def build_parser():
    p = argparse.ArgumentParser(
        prog="lk",
        description="县域低空飞行服务点 — 空域协调员命令行工具",
    )
    sub = p.add_subparsers(dest="command", help="可用命令")

    w = sub.add_parser("add-window", help="录入飞行窗口")
    w.add_argument("--date", help="日期(YYYY-MM-DD)，默认今天")
    w.add_argument("--start", required=True, help="开始时间(HH:MM)")
    w.add_argument("--end", required=True, help="结束时间(HH:MM)")
    w.add_argument("--alt-min", type=int, required=True, help="最低高度(m)")
    w.add_argument("--alt-max", type=int, required=True, help="最高高度(m)")
    w.add_argument("--township", required=True, help="乡镇")
    w.add_argument("--applicant", type=int, required=True, help="申请方ID")
    w.add_argument("--purpose", help="飞行用途")
    w.set_defaults(func=cmd_add_window)

    a = sub.add_parser("add-applicant", help="登记申请方")
    a.add_argument("--name", required=True, help="姓名/单位名")
    a.add_argument("--org", help="所属机构")
    a.add_argument("--phone", help="联系电话")
    a.add_argument("--atype", default="personal", help="类型(personal/org)")
    a.set_defaults(func=cmd_add_applicant)

    a2 = sub.add_parser("list-applicants", help="列出申请方")
    a2.set_defaults(func=cmd_list_applicants)

    s = sub.add_parser("mark-sensitive", help="标注学校医院活动点")
    s.add_argument("--name", required=True, help="名称")
    s.add_argument("--stype", required=True, choices=["school", "hospital", "event"], help="类型")
    s.add_argument("--township", required=True, help="乡镇")
    s.add_argument("--radius", type=int, default=500, help="半径(m)")
    s.add_argument("--note", help="备注")
    s.set_defaults(func=cmd_mark_sensitive)

    s2 = sub.add_parser("list-sensitive", help="列出敏感点")
    s2.set_defaults(func=cmd_list_sensitive)

    c = sub.add_parser("check-altitude", help="检查高度重叠")
    c.add_argument("--date", help="日期，默认今天")
    c.set_defaults(func=cmd_check_altitude)

    nf = sub.add_parser("add-nofly", help="添加临时禁飞")
    nf.add_argument("--township", required=True, help="乡镇")
    nf.add_argument("--reason", required=True, help="原因")
    nf.add_argument("--start", help="开始时间，默认当前")
    nf.add_argument("--end", help="结束时间")
    nf.add_argument("--date", help="日期，默认今天")
    nf.set_defaults(func=cmd_add_nofly)

    snf = sub.add_parser("show-nofly", help="提示临时禁飞")
    snf.add_argument("--date", help="日期，默认今天")
    snf.set_defaults(func=cmd_show_nofly)

    co = sub.add_parser("add-contact", help="登记联络人")
    co.add_argument("--name", required=True, help="姓名")
    co.add_argument("--role", help="职务/角色")
    co.add_argument("--phone", help="电话")
    co.add_argument("--township", help="乡镇")
    co.set_defaults(func=cmd_add_contact)

    co2 = sub.add_parser("list-contacts", help="列出联络人")
    co2.set_defaults(func=cmd_list_contacts)

    cf = sub.add_parser("confirm", help="记录放飞前确认（支持补录挂到业务日期）")
    cf.add_argument("--window-id", type=int, required=True, help="窗口ID")
    cf.add_argument("--confirmer", required=True, help="确认人")
    cf.add_argument("--biz-date", help="业务日期(YYYY-MM-DD)，默认取窗口飞行日")
    cf.add_argument("--notes", help="备注")
    cf.set_defaults(func=cmd_confirm)

    ab = sub.add_parser("abnormal", help="补记异常返航（支持补录挂到业务日期）")
    ab.add_argument("--window-id", type=int, required=True, help="窗口ID")
    ab.add_argument("--reason", required=True, help="原因")
    ab.add_argument("--biz-date", help="业务日期(YYYY-MM-DD)，默认取窗口飞行日")
    ab.add_argument("--time", help="返航时间，默认当前")
    ab.add_argument("--notes", help="备注")
    ab.set_defaults(func=cmd_abnormal)

    bc = sub.add_parser("broadcast", help="输出口头播报稿")
    bc.add_argument("--date", help="日期，默认今天")
    bc.set_defaults(func=cmd_broadcast)

    sm = sub.add_parser("sms", help="生成短信模板")
    sm.add_argument("--date", help="日期，默认今天")
    sm.set_defaults(func=cmd_sms)

    td = sub.add_parser("today", help="快速查询当天占用（带确认/复核/异常状态）")
    td.add_argument("--date", help="日期，默认今天")
    td.set_defaults(func=cmd_today)

    fl = sub.add_parser("conflict", help="按乡镇筛冲突")
    fl.add_argument("--township", required=True, help="乡镇")
    fl.add_argument("--date", help="日期，默认今天")
    fl.set_defaults(func=cmd_conflict)

    sd = sub.add_parser("set-duty", help="设置值班")
    sd.add_argument("--name", required=True, help="协调员姓名")
    sd.add_argument("--phone", help="电话")
    sd.add_argument("--date", help="日期，默认今天")
    sd.set_defaults(func=cmd_set_duty)

    du = sub.add_parser("duty", help="打印简版值班表")
    du.set_defaults(func=cmd_duty)

    ar = sub.add_parser("archive", help="归档已结束任务")
    ar.set_defaults(func=cmd_archive)

    st = sub.add_parser("streak", help="累计连续零漏报天数")
    st.set_defaults(func=cmd_streak)

    sr = sub.add_parser("star", help="给按时复核加星（同窗口同业务日去重，支持补录）")
    sr.add_argument("--window-id", type=int, required=True, help="窗口ID")
    sr.add_argument("--reviewer", required=True, help="复核人")
    sr.add_argument("--biz-date", help="业务日期(YYYY-MM-DD)，默认取窗口飞行日")
    sr.set_defaults(func=cmd_star)

    gp = sub.add_parser("gaps", help="补分关卡（区分正常完成/补录完成/仍待补）")
    gp.add_argument("--date", help="日期，默认今天")
    gp.set_defaults(func=cmd_gaps)

    ds = sub.add_parser("daily-summary", help="日结汇总：已确认/已复核/异常/冲突/遗漏 + streak 达标判断")
    ds.add_argument("--date", help="业务日期，默认今天")
    ds.set_defaults(func=cmd_daily_summary)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
