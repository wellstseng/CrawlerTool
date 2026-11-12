#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import sys
import threading
import time
import traceback
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chip_analysis import DAY_TRADE_RISK_RATIO, build_analysis, parse_analysis_date, write_output
from query_stock_data import DATASETS, DEFAULT_ROOT, connect
from technical_analysis import PRESETS, analyze, market_summary, screen


MARKETS = ("all", "twse", "tpex")
SYMBOL_RE = re.compile(r"^[0-9A-Za-z._-]{1,20}$")

# 操盤室面板 JSON（trading-room skill 產出；dashboard 只讀檔，不執行 wendy 端程式）
PANEL_JSON_PATH = Path(os.environ.get(
    "TRADING_ROOM_PANEL_JSON",
    str(Path.home() / ".catclaw" / "workspace" / "agents" / "wendy"
        / "skills" / "trading-room" / "data" / "panel.json"),
))


DASHBOARD_HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StockResource Dashboard</title>
  <style>
    :root {
      --bg: #f6f7f4;
      --panel: #ffffff;
      --ink: #1d252c;
      --muted: #647077;
      --line: #d8ded6;
      --soft: #eef2ee;
      --teal: #00796b;
      --blue: #2563eb;
      --red: #b3261e;
      --amber: #ad7a05;
      --green: #16803c;
      --shadow: 0 1px 2px rgba(17, 24, 39, 0.08);
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
      font-size: 14px;
      line-height: 1.45;
      letter-spacing: 0;
    }

    button, input, select {
      font: inherit;
      letter-spacing: 0;
    }

    .app {
      width: min(1520px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 18px 0 28px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 0 14px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 760;
      line-height: 1.1;
    }

    h2 {
      margin: 0;
      font-size: 15px;
      font-weight: 760;
    }

    .subtle {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
    }

    .control {
      height: 34px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 7px;
      padding: 0 10px;
      min-width: 112px;
      box-shadow: var(--shadow);
    }

    input.control { min-width: 120px; }

    .icon-button, .command {
      height: 34px;
      border: 1px solid #b9c7bd;
      background: #ffffff;
      color: var(--ink);
      border-radius: 7px;
      padding: 0 11px;
      cursor: pointer;
      box-shadow: var(--shadow);
      white-space: nowrap;
    }

    .command {
      background: var(--teal);
      border-color: var(--teal);
      color: #fff;
      font-weight: 700;
    }

    .icon-button:hover, .command:hover { filter: brightness(0.98); }
    .icon-button:disabled, .command:disabled { opacity: 0.55; cursor: wait; }

    .grid {
      display: grid;
      gap: 12px;
    }

    .grid.two { grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); }
    .grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
      min-width: 0;
    }

    .panel-head {
      min-height: 45px;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfa;
    }

    .panel-body { padding: 12px; }

    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }

    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: #ffffff;
      min-height: 72px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-width: 0;
    }

    .metric .label {
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .metric .value {
      font-size: 22px;
      font-weight: 780;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }

    .positive { color: var(--red); }
    .negative { color: var(--green); }
    .neutral { color: var(--muted); }
    .warn { color: var(--amber); }

    .split {
      display: grid;
      grid-template-columns: minmax(250px, 0.82fr) minmax(340px, 1.18fr);
      gap: 12px;
      align-items: start;
    }

    .chart {
      width: 100%;
      aspect-ratio: 2.45;
      min-height: 190px;
      max-height: 300px;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }

    .table-wrap {
      width: 100%;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 620px;
    }

    #industryTable { min-width: 360px; }

    th, td {
      padding: 8px 9px;
      border-bottom: 1px solid #edf0ec;
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
    }

    th {
      color: #46525a;
      background: #f7f9f6;
      font-size: 12px;
      font-weight: 760;
      position: sticky;
      top: 0;
      z-index: 1;
    }

    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    tr:last-child td { border-bottom: 0; }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: #344149;
      background: var(--soft);
      font-size: 12px;
      white-space: nowrap;
    }

    .status-line {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 28px;
      align-items: center;
    }

    .error {
      margin-bottom: 12px;
      border: 1px solid #e2a39d;
      background: #fff4f2;
      color: #7b1f18;
      border-radius: 8px;
      padding: 10px 12px;
      display: none;
      white-space: pre-wrap;
    }

    .stack {
      display: grid;
      gap: 12px;
    }

    .row-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }

    @media (max-width: 1080px) {
      .grid.two, .grid.three, .split { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      header { align-items: flex-start; flex-direction: column; }
      .toolbar { justify-content: flex-start; }
    }

    .alert-line {
      padding: 4px 10px; margin: 2px 0; font-size: 13px; border-radius: 4px;
      border-left: 3px solid #e8a03e; background: rgba(232, 160, 62, .08);
    }
    @media (max-width: 620px) {
      .app { width: min(100vw - 18px, 1520px); padding-top: 10px; }
      .metrics { grid-template-columns: 1fr; }
      .panel-head { align-items: flex-start; flex-direction: column; }
      .row-actions { justify-content: flex-start; }
      .control, input.control { min-width: 0; width: 100%; }
      .toolbar { width: 100%; }
      .toolbar > * { flex: 1 1 130px; }
    }
  </style>
</head>
<body>
  <main class="app">
    <header>
      <div>
        <h1>StockResource Dashboard</h1>
        <div id="statusLine" class="status-line"></div>
      </div>
      <div class="toolbar">
        <select id="marketSelect" class="control" aria-label="市場">
          <option value="all">全部市場</option>
          <option value="twse">上市</option>
          <option value="tpex">上櫃</option>
        </select>
        <button id="reloadBtn" class="icon-button" type="button" title="重新整理">↻</button>
      </div>
    </header>

    <div id="errorBox" class="error"></div>

    <section class="grid">
      <div class="panel">
        <div class="panel-head">
          <h2>🎛 操盤室</h2>
          <span id="panelMeta" class="subtle">--</span>
        </div>
        <div class="panel-body stack">
          <div id="panelAlerts"></div>
          <div class="split">
            <div class="table-wrap"><table id="panelPlanTable"></table></div>
            <div class="table-wrap"><table id="panelHoldingsTable"></table></div>
          </div>
          <div id="panelRegime" class="subtle"></div>
          <div id="panelRadar" class="subtle"></div>
          <div id="panelCrons"></div>
        </div>
      </div>
    </section>

    <section class="grid two">
      <div class="panel">
        <div class="panel-head">
          <h2>市場總覽</h2>
          <span id="summaryDate" class="subtle">--</span>
        </div>
        <div class="panel-body stack">
          <div id="summaryMetrics" class="metrics"></div>
          <div class="split">
            <div class="chart"><canvas id="breadthChart"></canvas></div>
            <div class="table-wrap"><table id="volumeTable"></table></div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>三大法人與資金流</h2>
          <span id="chipDate" class="subtle">--</span>
        </div>
        <div class="panel-body stack">
          <div id="chipMetrics" class="metrics"></div>
          <div class="split">
            <div class="chart"><canvas id="industryChart"></canvas></div>
            <div class="table-wrap"><table id="industryTable"></table></div>
          </div>
        </div>
      </div>
    </section>

    <section class="grid two" style="margin-top: 12px;">
      <div class="panel">
        <div class="panel-head">
          <h2>條件掃描</h2>
          <div class="row-actions">
            <select id="presetSelect" class="control" aria-label="條件">
              <option value="breakout_20d">20日突破</option>
              <option value="volume_surge">爆量</option>
              <option value="ma_bullish_alignment">多頭排列</option>
              <option value="macd_bullish_cross">MACD 黃金交叉</option>
              <option value="rsi_oversold">RSI 偏低</option>
              <option value="near_52w_high">接近52週高</option>
              <option value="breakdown_20d">20日跌破</option>
            </select>
            <button id="screenBtn" class="command" type="button">掃描</button>
          </div>
        </div>
        <div class="panel-body">
          <div class="table-wrap"><table id="screenTable"></table></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>單股技術面</h2>
          <div class="row-actions">
            <input id="symbolInput" class="control" value="2330" maxlength="20" aria-label="股票">
            <button id="symbolBtn" class="command" type="button">分析</button>
          </div>
        </div>
        <div class="panel-body stack">
          <div id="symbolMetrics" class="metrics"></div>
          <div id="signalChips" class="chips"></div>
          <div class="chart"><canvas id="symbolChart"></canvas></div>
        </div>
      </div>
    </section>

    <section class="grid three" style="margin-top: 12px;">
      <div class="panel">
        <div class="panel-head">
          <h2>法人排行</h2>
          <select id="legalRankSelect" class="control" aria-label="法人排行">
            <option value="foreign.buy">外資買超</option>
            <option value="foreign.sell">外資賣超</option>
            <option value="investment_trust.buy">投信買超</option>
            <option value="investment_trust.sell">投信賣超</option>
            <option value="dealer.buy">自營買超</option>
            <option value="dealer.sell">自營賣超</option>
          </select>
        </div>
        <div class="panel-body">
          <div class="table-wrap"><table id="legalRankTable"></table></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>融資與當沖</h2>
          <select id="heatSelect" class="control" aria-label="熱度">
            <option value="margin.increase">融資增加</option>
            <option value="margin.decrease">融資減少</option>
            <option value="day_trading_heat">當沖熱度</option>
          </select>
        </div>
        <div class="panel-body">
          <div class="table-wrap"><table id="heatTable"></table></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>背離訊號</h2>
          <select id="divergenceSelect" class="control" aria-label="背離">
            <option value="price_up_foreign_sell">價漲外資賣</option>
            <option value="price_down_investment_trust_buy">價跌投信買</option>
            <option value="margin_increase_price_weak">融資增股價弱</option>
            <option value="high_day_trading_ratio_risk">當沖比風險</option>
          </select>
        </div>
        <div class="panel-body">
          <div class="table-wrap"><table id="divergenceTable"></table></div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const state = { status: null, summary: null, chip: null, symbol: null, busy: 0 };

    const $ = (id) => document.getElementById(id);

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[ch]));
    }

    function fmtNum(value) {
      if (value === null || value === undefined || value === "") return "--";
      const n = Number(value);
      if (!Number.isFinite(n)) return escapeHtml(value);
      const abs = Math.abs(n);
      if (abs >= 100000000) return `${(n / 100000000).toFixed(2)}億`;
      if (abs >= 10000) return `${(n / 10000).toFixed(2)}萬`;
      if (abs >= 1000) return Math.round(n).toLocaleString("zh-TW");
      if (Number.isInteger(n)) return n.toLocaleString("zh-TW");
      return n.toFixed(2);
    }

    function fmtPct(value) {
      if (value === null || value === undefined || value === "") return "--";
      const n = Number(value);
      if (!Number.isFinite(n)) return escapeHtml(value);
      return `${n.toFixed(2)}%`;
    }

    function fmtPrice(value) {
      if (value === null || value === undefined || value === "") return "--";
      const n = Number(value);
      if (!Number.isFinite(n)) return escapeHtml(value);
      return n >= 100 ? n.toFixed(1) : n.toFixed(2);
    }

    function classByNumber(value) {
      const n = Number(value);
      if (!Number.isFinite(n) || n === 0) return "neutral";
      return n > 0 ? "positive" : "negative";
    }

    function setBusy(on) {
      state.busy += on ? 1 : -1;
      state.busy = Math.max(0, state.busy);
      $("reloadBtn").disabled = state.busy > 0;
      $("screenBtn").disabled = state.busy > 0;
      $("symbolBtn").disabled = state.busy > 0;
    }

    function showError(message) {
      const box = $("errorBox");
      if (!message) {
        box.style.display = "none";
        box.textContent = "";
        return;
      }
      box.style.display = "block";
      box.textContent = message;
    }

    async function api(path, params = {}) {
      const url = new URL(path, window.location.origin);
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
      }
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
      return data;
    }

    function metric(label, value, cls = "") {
      return `<div class="metric"><div class="label">${escapeHtml(label)}</div><div class="value ${cls}">${escapeHtml(value)}</div></div>`;
    }

    function tableHtml(rows, columns, emptyText = "無資料") {
      if (!rows || rows.length === 0) {
        return `<thead><tr><th>${escapeHtml(emptyText)}</th></tr></thead><tbody></tbody>`;
      }
      const head = `<thead><tr>${columns.map(c => `<th class="${c.num ? "num" : ""}">${escapeHtml(c.label)}</th>`).join("")}</tr></thead>`;
      const body = rows.map(row => {
        return `<tr>${columns.map(c => {
          const raw = row[c.key];
          const value = c.fmt ? c.fmt(raw, row) : raw;
          const cls = [c.num ? "num" : "", c.cls ? c.cls(raw, row) : ""].filter(Boolean).join(" ");
          return `<td class="${cls}">${escapeHtml(value)}</td>`;
        }).join("")}</tr>`;
      }).join("");
      return `${head}<tbody>${body}</tbody>`;
    }

    function setTable(id, rows, columns, emptyText) {
      $(id).innerHTML = tableHtml(rows, columns, emptyText);
    }

    function canvasContext(canvas) {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(320, rect.width);
      const height = Math.max(180, rect.height);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      return { ctx, width, height };
    }

    function drawBreadth(summary) {
      const canvas = $("breadthChart");
      const { ctx, width, height } = canvasContext(canvas);
      const universe = summary?.universe || {};
      const items = [
        { label: "上漲", value: universe.up || 0, color: "#b3261e" },
        { label: "下跌", value: universe.down || 0, color: "#16803c" },
        { label: "平盤", value: universe.flat || 0, color: "#8a935d" },
      ];
      const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
      const x = 18, y = 54, barW = width - 36, barH = 30;
      ctx.fillStyle = "#f0f3ef";
      ctx.fillRect(x, y, barW, barH);
      let offset = 0;
      items.forEach(item => {
        const w = barW * item.value / total;
        ctx.fillStyle = item.color;
        ctx.fillRect(x + offset, y, w, barH);
        offset += w;
      });
      ctx.fillStyle = "#1d252c";
      ctx.font = "700 15px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText(`漲跌家數 ${universe.up || 0} / ${universe.down || 0} / ${universe.flat || 0}`, x, 27);
      ctx.font = "12px -apple-system, BlinkMacSystemFont, sans-serif";
      let lx = x;
      items.forEach(item => {
        ctx.fillStyle = item.color;
        ctx.fillRect(lx, height - 38, 10, 10);
        ctx.fillStyle = "#4b565d";
        ctx.fillText(`${item.label} ${Math.round(item.value / total * 100)}%`, lx + 15, height - 29);
        lx += 88;
      });
    }

    function drawIndustry(rows) {
      const canvas = $("industryChart");
      const { ctx, width, height } = canvasContext(canvas);
      const data = (rows || []).slice(0, 9);
      const values = data.map(row => Number(row.total_net || 0));
      const max = Math.max(1, ...values.map(v => Math.abs(v)));
      const left = 88, right = 16, top = 18, rowH = Math.max(18, (height - 34) / Math.max(1, data.length));
      ctx.font = "12px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = "#647077";
      ctx.fillText("產業法人淨流向", 12, 13);
      data.forEach((row, i) => {
        const y = top + i * rowH + 4;
        const name = (row.industry || "未分類").slice(0, 8);
        const v = Number(row.total_net || 0);
        const zero = left + (width - left - right) / 2;
        const barMax = (width - left - right) / 2;
        const w = Math.abs(v) / max * barMax;
        ctx.fillStyle = "#4b565d";
        ctx.fillText(name, 12, y + 11);
        ctx.fillStyle = "#edf0ec";
        ctx.fillRect(left, y, width - left - right, 12);
        ctx.fillStyle = v >= 0 ? "#b3261e" : "#16803c";
        ctx.fillRect(v >= 0 ? zero : zero - w, y, w, 12);
      });
    }

    function drawSymbol(series) {
      const canvas = $("symbolChart");
      const { ctx, width, height } = canvasContext(canvas);
      const rows = series || [];
      if (!rows.length) return;
      const keys = [
        { key: "close", color: "#1d252c", width: 2 },
        { key: "sma_20", color: "#2563eb", width: 1.5 },
        { key: "sma_60", color: "#ad7a05", width: 1.5 },
      ];
      const values = [];
      rows.forEach(row => keys.forEach(k => {
        const n = Number(row[k.key]);
        if (Number.isFinite(n)) values.push(n);
      }));
      if (!values.length) return;
      const min = Math.min(...values);
      const max = Math.max(...values);
      const pad = Math.max(1, (max - min) * 0.08);
      const yMin = min - pad, yMax = max + pad;
      const left = 44, right = 14, top = 18, bottom = 28;
      const plotW = width - left - right;
      const plotH = height - top - bottom;
      const xAt = i => left + (rows.length === 1 ? 0 : i / (rows.length - 1) * plotW);
      const yAt = v => top + (yMax - v) / (yMax - yMin) * plotH;
      ctx.strokeStyle = "#d8ded6";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i <= 4; i++) {
        const y = top + i / 4 * plotH;
        ctx.moveTo(left, y);
        ctx.lineTo(width - right, y);
      }
      ctx.stroke();
      ctx.fillStyle = "#647077";
      ctx.font = "11px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText(fmtPrice(yMax), 4, top + 4);
      ctx.fillText(fmtPrice(yMin), 4, top + plotH);
      keys.forEach(k => {
        ctx.strokeStyle = k.color;
        ctx.lineWidth = k.width;
        ctx.beginPath();
        let started = false;
        rows.forEach((row, i) => {
          const n = Number(row[k.key]);
          if (!Number.isFinite(n)) return;
          const x = xAt(i), y = yAt(n);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        });
        ctx.stroke();
      });
      const legend = [["收盤", "#1d252c"], ["SMA20", "#2563eb"], ["SMA60", "#ad7a05"]];
      let lx = left;
      legend.forEach(item => {
        ctx.fillStyle = item[1];
        ctx.fillRect(lx, height - 17, 10, 10);
        ctx.fillStyle = "#4b565d";
        ctx.fillText(item[0], lx + 15, height - 8);
        lx += 72;
      });
    }

    function renderStatus(data) {
      state.status = data;
      const datasets = data.datasets || {};
      const parts = [];
      if (datasets.price?.max_date) parts.push(`<span class="chip">price ${escapeHtml(datasets.price.max_date)}</span>`);
      if (datasets.legal_person?.max_date) parts.push(`<span class="chip">legal ${escapeHtml(datasets.legal_person.max_date)}</span>`);
      parts.push(`<span class="chip">${escapeHtml(data.root)}</span>`);
      $("statusLine").innerHTML = parts.join("");
    }

    function renderSummary(data) {
      state.summary = data;
      const u = data.universe || {};
      const b = data.breadth || {};
      $("summaryDate").textContent = `${data.date || "--"} · ${data.market || "all"}`;
      $("summaryMetrics").innerHTML = [
        metric("標的數", fmtNum(u.symbols), "neutral"),
        metric("上漲比", fmtPct(u.up_ratio), classByNumber((u.up || 0) - (u.down || 0))),
        metric("站上 SMA20", fmtPct(b.above_sma20_ratio), classByNumber((b.above_sma20_ratio || 0) - 50)),
        metric("20日突破", fmtNum(b.breakout_20d), "positive"),
      ].join("");
      setTable("volumeTable", data.top?.volume_surge || [], stockColumns(), "無爆量資料");
      requestAnimationFrame(() => drawBreadth(data));
    }

    function renderChip(data) {
      state.chip = data;
      const totals = data.totals || {};
      $("chipDate").textContent = `${data.date || "--"} · ${data._dashboard?.source || "live"}`;
      $("chipMetrics").innerHTML = [
        metric("外資", fmtNum(totals.foreign_net), classByNumber(totals.foreign_net)),
        metric("投信", fmtNum(totals.investment_trust_net), classByNumber(totals.investment_trust_net)),
        metric("自營", fmtNum(totals.dealer_net), classByNumber(totals.dealer_net)),
        metric("合計", fmtNum(totals.total_net), classByNumber(totals.total_net)),
      ].join("");
      setTable("industryTable", data.industry_flow || [], [
        { key: "industry", label: "產業" },
        { key: "symbols", label: "檔數", num: true, fmt: fmtNum },
        { key: "total_net", label: "合計", num: true, fmt: fmtNum, cls: classByNumber },
      ], "無產業資料");
      renderLegalRank();
      renderHeat();
      renderDivergence();
      requestAnimationFrame(() => drawIndustry(data.industry_flow || []));
    }

    function stockColumns(extra = []) {
      return [
        { key: "symbol", label: "代號" },
        { key: "name", label: "名稱" },
        { key: "close", label: "收盤", num: true, fmt: fmtPrice },
        { key: "change_pct", label: "漲跌", num: true, fmt: fmtPct, cls: classByNumber },
        { key: "volume_ratio_20", label: "量比", num: true, fmt: fmtNum },
        ...extra,
      ];
    }

    function renderLegalRank() {
      const data = state.chip;
      if (!data) return;
      const [person, side] = $("legalRankSelect").value.split(".");
      const rows = data.rankings?.[person]?.[side] || [];
      setTable("legalRankTable", rows, stockColumns([
        { key: "net", label: "買賣超", num: true, fmt: fmtNum, cls: classByNumber },
      ]), "無法人資料");
    }

    function renderHeat() {
      const data = state.chip;
      if (!data) return;
      const value = $("heatSelect").value;
      let rows = [];
      let cols = stockColumns();
      if (value === "day_trading_heat") {
        rows = data.day_trading_heat || [];
        cols = stockColumns([
          { key: "day_trade_ratio", label: "當沖比", num: true, fmt: fmtPct, cls: v => Number(v) >= 30 ? "warn" : "" },
          { key: "day_trade_volume", label: "當沖量", num: true, fmt: fmtNum },
        ]);
      } else {
        const [group, side] = value.split(".");
        rows = data[group]?.[side] || [];
        cols = stockColumns([
          { key: "margin_balance_change", label: "融資增減", num: true, fmt: fmtNum, cls: classByNumber },
          { key: "margin_balance", label: "融資餘額", num: true, fmt: fmtNum },
        ]);
      }
      setTable("heatTable", rows, cols, "無資料");
    }

    function renderDivergence() {
      const data = state.chip;
      if (!data) return;
      const key = $("divergenceSelect").value;
      const rows = data.divergence_signals?.[key] || [];
      const extras = [];
      if (key.includes("foreign")) extras.push({ key: "foreign_net", label: "外資", num: true, fmt: fmtNum, cls: classByNumber });
      if (key.includes("investment")) extras.push({ key: "investment_trust_net", label: "投信", num: true, fmt: fmtNum, cls: classByNumber });
      if (key.includes("margin")) extras.push({ key: "margin_balance_change", label: "融資增減", num: true, fmt: fmtNum, cls: classByNumber });
      if (key.includes("day_trading")) extras.push({ key: "day_trade_ratio", label: "當沖比", num: true, fmt: fmtPct, cls: v => Number(v) >= 30 ? "warn" : "" });
      setTable("divergenceTable", rows, stockColumns(extras), "無背離資料");
    }

    function renderScreen(data) {
      setTable("screenTable", data.rows || [], [
        { key: "symbol", label: "代號" },
        { key: "name", label: "名稱" },
        { key: "close", label: "收盤", num: true, fmt: fmtPrice },
        { key: "change_pct", label: "漲跌", num: true, fmt: fmtPct, cls: classByNumber },
        { key: "volume_ratio_20", label: "量比", num: true, fmt: fmtNum },
        { key: "rsi_14", label: "RSI", num: true, fmt: fmtNum },
        { key: "signals", label: "訊號", fmt: v => (v || []).join(", ") },
      ], "無符合標的");
    }

    function renderSymbol(data) {
      state.symbol = data;
      const latest = data.latest || {};
      const joined = data.latest_joined || {};
      $("symbolMetrics").innerHTML = [
        metric(`${data.symbol} ${latest.name || ""}`, fmtPrice(latest.close), classByNumber(data.change_pct)),
        metric("RSI", fmtNum(latest.rsi_14), Number(latest.rsi_14) >= 70 ? "warn" : Number(latest.rsi_14) <= 30 ? "positive" : "neutral"),
        metric("SMA20距離", fmtPct(data.pct_from_sma20), classByNumber(data.pct_from_sma20)),
        metric("法人合計", fmtNum(joined.total_net), classByNumber(joined.total_net)),
      ].join("");
      $("signalChips").innerHTML = (data.signals || []).map(s => `<span class="chip">${escapeHtml(s)}</span>`).join("");
      requestAnimationFrame(() => drawSymbol(data.series || []));
    }

    async function loadStatus() {
      const data = await api("/api/status");
      renderStatus(data);
    }

    async function loadSummary(refresh = false) {
      const market = $("marketSelect").value;
      const data = await api("/api/summary", { market, refresh: refresh ? 1 : "" });
      renderSummary(data);
    }

    async function loadChip(refresh = false) {
      const data = await api("/api/chip", { date: "latest", refresh: refresh ? 1 : "" });
      renderChip(data);
    }

    async function loadScreen() {
      const market = $("marketSelect").value;
      const preset = $("presetSelect").value;
      const data = await api("/api/screen", { market, preset, limit: 30 });
      renderScreen(data);
    }

    async function loadSymbol() {
      const market = $("marketSelect").value;
      const symbol = $("symbolInput").value.trim();
      if (!symbol) return;
      const data = await api("/api/symbol", { market, symbol, series_limit: 180 });
      renderSymbol(data);
    }

    async function run(action) {
      showError("");
      setBusy(true);
      try {
        await action();
      } catch (err) {
        showError(err.message || String(err));
      } finally {
        setBusy(false);
      }
    }

    function stripMd(s) { return String(s || "").replace(/\*\*/g, ""); }
    const moneyFmt = v => (typeof v === "number" ? v.toLocaleString("zh-TW", { maximumFractionDigits: 0 }) : "—");
    const pctFmt = v => (typeof v === "number" ? `${v.toFixed(1)}%` : "—");

    async function loadPanel() {
      let data;
      try {
        data = await api("/api/panel");
      } catch (err) {
        $("panelMeta").textContent = "無法取得面板資料";
        return;
      }
      if (!data.available) {
        $("panelMeta").textContent = data.reason || "panel.json 尚未生成";
        return;
      }
      const p = data.panel;
      $("panelMeta").textContent = `${p.date} · 生成 ${String(p.generated_at || "").slice(11, 16)}`
        + (p.is_trading_day ? "" : " · 非交易日");
      $("panelAlerts").innerHTML = (p.alerts && p.alerts.length)
        ? p.alerts.map(a => `<div class="alert-line">${escapeHtml(stripMd(a))}</div>`).join("")
        : `<div class="subtle">✅ 無警示</div>`;
      const bp = p.buildplan || {};
      setTable("panelPlanTable", bp.broken ? [] : (bp.rows || []), [
        { key: "name", label: "建倉標的" },
        { key: "remaining", label: "剩餘子彈", num: true, fmt: moneyFmt },
        { key: "seg_done", label: "段數", fmt: (v, r) => (r.seg_total ? `${v}/${r.seg_total}` : "—") },
        { key: "from_high", label: "距近高", num: true, fmt: pctFmt },
      ], bp.broken ? "buildplan 損壞" : "無建倉資料");
      const hd = p.holdings || {};
      setTable("panelHoldingsTable", hd.rows || [], [
        { key: "name", label: "持倉" },
        { key: "qty", label: "股數", num: true, fmt: moneyFmt },
        { key: "close", label: "現價", num: true },
        { key: "pnl", label: "損益", num: true, fmt: moneyFmt },
        { key: "pnl_pct", label: "報酬率", num: true },
      ], hd.error || "無持倉資料");
      const rg = p.regime;
      const rq = p.regression;
      $("panelRegime").innerHTML = rg
        ? `大盤：<strong>${escapeHtml(rg.market_status || "?")}</strong> score ${escapeHtml(String(rg.score == null ? "?" : rg.score))} ${escapeHtml(rg.fresh_label || "")}`
          + (rq ? `｜品質層 ${escapeHtml(rq.grade || "?")} / ${escapeHtml(rq.confidence || "?")}` : "")
        : "大盤：無 regime 資料";
      const bits = [];
      const pr = (p.radar || {}).pullback;
      if (pr) bits.push(`核心ETF回調 <strong>${escapeHtml(pr.status || "?")}</strong>（${escapeHtml(pr.slot || "?")}）`
        + (pr.stocks || []).map(s => `${escapeHtml(s.name || "")} ${pctFmt(s.from_high_pct)}`).join("、"));
      const l6 = (p.radar || {}).l631;
      if (l6) bits.push(`00631L <strong>${escapeHtml(l6.status || "?")}</strong>（${escapeHtml(l6.slot || "?")}）`);
      $("panelRadar").innerHTML = bits.length ? `盤中雷達：${bits.join("｜")}` : "盤中雷達：今日無落檔";
      const cronIcon = { ok: "✅", error: "❌", disabled: "⏸", missing: "❓" };
      $("panelCrons").innerHTML = (p.crons || []).map(c =>
        `<span class="chip">${cronIcon[c.state] || "?"} ${escapeHtml(c.label)}</span>`).join(" ");
    }

    async function boot() {
      await run(async () => {
        await loadStatus();
        await Promise.all([loadPanel(), loadSummary(), loadChip(), loadSymbol()]);
      });
    }

    $("reloadBtn").addEventListener("click", () => run(async () => {
      await loadStatus();
      await Promise.all([loadPanel(), loadSummary(true), loadChip(false), loadSymbol()]);
    }));
    setInterval(() => { loadPanel(); }, 60000);
    $("screenBtn").addEventListener("click", () => run(loadScreen));
    $("symbolBtn").addEventListener("click", () => run(loadSymbol));
    $("symbolInput").addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") run(loadSymbol);
    });
    $("marketSelect").addEventListener("change", () => run(async () => {
      await Promise.all([loadSummary(true), loadSymbol()]);
      $("screenTable").innerHTML = tableHtml([], [{ key: "symbol", label: "代號" }], "未掃描");
    }));
    $("legalRankSelect").addEventListener("change", renderLegalRank);
    $("heatSelect").addEventListener("change", renderHeat);
    $("divergenceSelect").addEventListener("change", renderDivergence);
    window.addEventListener("resize", () => {
      if (state.summary) drawBreadth(state.summary);
      if (state.chip) drawIndustry(state.chip.industry_flow || []);
      if (state.symbol) drawSymbol(state.symbol.series || []);
    });

    boot();
  </script>
</body>
</html>
"""


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def rows_to_dicts(cursor):
    columns = [item[0] for item in cursor.description]
    result = []
    for row in cursor.fetchall():
        result.append({column: json_value(value) for column, value in zip(columns, row)})
    return result


def first(query, key, default=None):
    values = query.get(key)
    if not values:
        return default
    return values[0]


def int_param(query, key, default, minimum=None, maximum=None):
    raw = first(query, key)
    if raw in (None, ""):
        return default
    value = int(raw)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def bool_param(query, key):
    return first(query, key, "") in ("1", "true", "yes", "on")


def market_param(query):
    value = first(query, "market", "all")
    if value not in MARKETS:
        raise ValueError("bad market: {0}".format(value))
    return value


def date_param(query):
    value = first(query, "date", "")
    if not value or value == "latest":
        return None
    return value


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, root, cache_ttl, debug):
        super().__init__(address, handler)
        self.root = Path(root)
        self.cache_ttl = cache_ttl
        self.debug = debug
        self.cache = {}
        self.cache_lock = threading.Lock()


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "StockDashboard/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self.send_html(DASHBOARD_HTML)
            elif parsed.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            elif parsed.path == "/api/status":
                self.send_json(self.api_status(query))
            elif parsed.path == "/api/summary":
                self.send_json(self.api_summary(query))
            elif parsed.path == "/api/screen":
                self.send_json(self.api_screen(query))
            elif parsed.path == "/api/symbol":
                self.send_json(self.api_symbol(query))
            elif parsed.path == "/api/chip":
                self.send_json(self.api_chip(query))
            elif parsed.path == "/api/panel":
                self.send_json(self.api_panel(query))
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            payload = {"error": str(exc)}
            if self.server.debug:
                payload["trace"] = traceback.format_exc()
            self.send_json(payload, status=500)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (
            self.address_string(),
            self.log_date_time_string(),
            fmt % args,
        ))

    def send_html(self, body):
        data = body.encode("utf8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def cached(self, key, refresh, builder, ttl=None):
        ttl = self.server.cache_ttl if ttl is None else ttl
        now = time.time()
        with self.server.cache_lock:
            item = self.server.cache.get(key)
            if item and not refresh and now - item[0] <= ttl:
                return item[1]

        payload = builder()
        with self.server.cache_lock:
            self.server.cache[key] = (time.time(), payload)
        return payload

    def open_db(self):
        return connect(self.server.root)

    def api_status(self, query):
        refresh = bool_param(query, "refresh")

        def build():
            con = self.open_db()
            try:
                datasets = {}
                for name in DATASETS:
                    if name == "stock_list":
                        row = con.execute("select count(*) from stock_list").fetchone()
                        datasets[name] = {"rows": row[0], "min_date": None, "max_date": None}
                    else:
                        row = con.execute(
                            "select count(*) as rows, min(date) as min_date, max(date) as max_date from {0}".format(name)
                        ).fetchone()
                        datasets[name] = {
                            "rows": row[0],
                            "min_date": json_value(row[1]),
                            "max_date": json_value(row[2]),
                        }
                return {
                    "root": str(self.server.root),
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "datasets": datasets,
                }
            finally:
                con.close()

        return self.cached(("status",), refresh, build, ttl=120)

    def api_panel(self, query):
        p = PANEL_JSON_PATH
        if not p.exists():
            return {"available": False,
                    "reason": "panel.json 尚未生成（先跑 trading-room 的 build_panel.py）"}
        try:
            panel = json.loads(p.read_text(encoding="utf8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {"available": False, "reason": "panel.json 讀取失敗：{0}".format(exc)}
        return {
            "available": True,
            "panel": panel,
            "file_mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
        }

    def api_summary(self, query):
        refresh = bool_param(query, "refresh")
        market = market_param(query)
        limit = int_param(query, "limit", 12, 1, 50)
        lookback = int_param(query, "lookback", 300, 80, 500)
        requested_date = date_param(query)
        key = ("summary", market, requested_date, limit, lookback)

        def build():
            con = self.open_db()
            try:
                args = SimpleNamespace(
                    market=market,
                    date=requested_date,
                    lookback=lookback,
                    symbol_regex="^[0-9]{4}$",
                    limit=limit,
                    filter_outliers=True,
                    include_stale=False,
                )
                return market_summary(con, args)
            finally:
                con.close()

        return self.cached(key, refresh, build)

    def api_screen(self, query):
        refresh = bool_param(query, "refresh")
        market = market_param(query)
        preset = first(query, "preset", "breakout_20d")
        if preset not in PRESETS:
            raise ValueError("bad preset: {0}".format(preset))
        limit = int_param(query, "limit", 30, 1, 100)
        lookback = int_param(query, "lookback", 300, 80, 500)
        requested_date = date_param(query)
        key = ("screen", market, preset, requested_date, limit, lookback)

        def build():
            con = self.open_db()
            try:
                args = SimpleNamespace(
                    preset=preset,
                    market=market,
                    date=requested_date,
                    lookback=lookback,
                    symbol_regex="^[0-9]{4}$",
                    limit=limit,
                    sort="volume_ratio_20",
                    asc=False,
                    filter_outliers=True,
                    include_stale=False,
                )
                return screen(con, args)
            finally:
                con.close()

        return self.cached(key, refresh, build)

    def api_symbol(self, query):
        refresh = bool_param(query, "refresh")
        market = market_param(query)
        symbol = first(query, "symbol", "2330").strip()
        if not SYMBOL_RE.match(symbol):
            raise ValueError("bad symbol: {0}".format(symbol))
        lookback = int_param(query, "lookback", 300, 80, 800)
        series_limit = int_param(query, "series_limit", 180, 20, 500)
        key = ("symbol", market, symbol, lookback, series_limit)

        def build():
            con = self.open_db()
            try:
                args = SimpleNamespace(
                    symbol=symbol,
                    market=market,
                    start=None,
                    end=None,
                    lookback=lookback,
                    adjusted=False,
                    filter_outliers=True,
                    series_limit=series_limit,
                )
                result = analyze(con, args)
                latest = result.get("latest", {})
                result["change_pct"] = None
                close = latest.get("close")
                series = result.get("series", [])
                if close is not None and len(series) >= 2 and series[-2].get("close"):
                    result["change_pct"] = round((close / series[-2]["close"] - 1) * 100, 4)
                result["pct_from_sma20"] = None
                sma20 = latest.get("sma_20")
                if close is not None and sma20:
                    result["pct_from_sma20"] = round((close / sma20 - 1) * 100, 4)
                result["latest_joined"] = self.latest_joined(con, symbol, market)
                return result
            finally:
                con.close()

        return self.cached(key, refresh, build, ttl=120)

    def latest_joined(self, con, symbol, market):
        filters = ["p.symbol = ?"]
        params = [symbol]
        if market != "all":
            filters.append("p.market = ?")
            params.append(market)
        cursor = con.execute(
            """
            select
                p.date,
                p.market,
                p.symbol,
                p.name,
                p.close,
                l.foreign_net,
                l.investment_trust_net,
                l.dealer_net,
                l.total_net,
                m.margin_balance,
                d.day_trade_volume
            from price p
            left join legal_person l
                on p.date = l.date and p.market = l.market and p.symbol = l.symbol
            left join margin m
                on p.date = m.date and p.market = m.market and p.symbol = m.symbol
            left join day_trading d
                on p.date = d.date and p.market = d.market and p.symbol = d.symbol
            where {filters}
            order by p.date desc
            limit 1
            """.format(filters=" and ".join(filters)),
            params,
        )
        rows = rows_to_dicts(cursor)
        return rows[0] if rows else {}

    def api_chip(self, query):
        refresh = bool_param(query, "refresh")
        limit = int_param(query, "limit", 20, 1, 80)
        risk_ratio = float(first(query, "day_trade_risk_ratio", DAY_TRADE_RISK_RATIO))
        requested_date = first(query, "date", "latest")
        key = ("chip", requested_date, limit, risk_ratio)

        def build():
            con = self.open_db()
            try:
                target_date = parse_analysis_date(requested_date, con)
                path = self.server.root / "analysis" / "{0}_chip_analysis.json".format(target_date.isoformat())
                if path.exists() and not refresh:
                    with path.open("r", encoding="utf8") as f:
                        analysis = json.load(f)
                    analysis["_dashboard"] = {"source": "file", "path": str(path)}
                    return analysis
                analysis = build_analysis(con, self.server.root, target_date, limit, risk_ratio)
                output = write_output(self.server.root, target_date, analysis, None)
                analysis["_dashboard"] = {"source": "rebuilt", "path": str(output)}
                return analysis
            finally:
                con.close()

        return self.cached(key, refresh, build, ttl=300)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache-ttl", type=int, default=300)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    server = DashboardServer((args.host, args.port), DashboardHandler, args.root, args.cache_ttl, args.debug)
    url = "http://{0}:{1}/".format(args.host, args.port)
    print(url, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
