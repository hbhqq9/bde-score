#!/usr/bin/env node
/**
 * BDE Score™ MCP Server — Claude Code Plugin Entry Point
 * =======================================================
 * Self-contained MCP server for multi-factor stock scoring.
 * No external API keys required. Uses Yahoo Finance for data.
 *
 * Tools:
 *   score_stock      - Score a single stock (7-factor model)
 *   batch_score      - Score multiple stocks in one call
 *   top_performers   - Top N stocks by composite score
 *   worst_performers - Bottom N stocks by composite score
 *   market_overview  - Market sentiment + VIX level
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { fetchStockData, fetchMultipleStocks, isValidSymbol } from "./market-data.js";
import { analyzeStock, analyzePortfolio, getMarketSentiment } from "./scoring.js";

// Default watchlist
const DEFAULT_WATCHLIST = [
  "AAPL", "MSFT", "GOOG", "AMZN", "META", "NVDA", "AMD", "AVGO", "ARM", "INTC",
  "V", "MA", "JNJ", "UNH", "LLY", "PFE", "PG", "KO", "WMT", "MCD",
  "TSLA", "NFLX", "BABA", "SPY", "QQQ"
];

// Create MCP server
const server = new McpServer({
  name: "bde-score",
  version: "1.0.0",
});

// ============================================================
// Tool: score_stock
// ============================================================
server.tool(
  "score_stock",
  "Score a single stock using 7-factor composite model (VIX, Volume Profile, RSI, MACD, Bollinger, OBV, ATR). Returns composite score (0-100), signal classification, and factor breakdown.",
  {
    symbol: {
      type: "string",
      description: "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)",
    },
  },
  async ({ symbol }) => {
    if (!isValidSymbol(symbol)) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: `Invalid symbol: ${symbol}` }) }],
        isError: true,
      };
    }

    const data = await fetchStockData(symbol.toUpperCase());
    if (!data) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: `Failed to fetch data for ${symbol}` }) }],
        isError: true,
      };
    }

    const result = analyzeStock(data);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// ============================================================
// Tool: batch_score
// ============================================================
server.tool(
  "batch_score",
  "Score multiple stocks in one call. Returns ranked results with composite scores and factor breakdowns for each stock.",
  {
    symbols: {
      type: "array",
      items: { type: "string" },
      description: "Array of stock ticker symbols (e.g., [\"AAPL\", \"MSFT\", \"NVDA\"])",
    },
  },
  async ({ symbols }) => {
    if (!symbols || symbols.length === 0) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: "No symbols provided" }) }],
        isError: true,
      };
    }

    if (symbols.length > 20) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: "Maximum 20 symbols per batch" }) }],
        isError: true,
      };
    }

    const validSymbols = symbols.filter(isValidSymbol);
    const stockDataList = await fetchMultipleStocks(validSymbols);
    const results = analyzePortfolio(stockDataList);

    return {
      content: [{ type: "text", text: JSON.stringify(results, null, 2) }],
    };
  }
);

// ============================================================
// Tool: top_performers
// ============================================================
server.tool(
  "top_performers",
  "Get top N performing stocks from a watchlist, sorted by composite score descending.",
  {
    symbols: {
      type: "array",
      items: { type: "string" },
      description: "Array of stock tickers to analyze (defaults to built-in 25-stock watchlist)",
    },
    limit: {
      type: "number",
      description: "Number of top performers to return (default: 5)",
    },
  },
  async ({ symbols, limit }) => {
    const watchlist = (symbols && symbols.length > 0) ? symbols.filter(isValidSymbol) : DEFAULT_WATCHLIST;
    const count = Math.min(limit || 5, 25);

    const stockDataList = await fetchMultipleStocks(watchlist);
    const results = analyzePortfolio(stockDataList);
    const topPerformers = results.rankings.slice(0, count);

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          analyzedAt: results.analyzedAt,
          topN: count,
          watchlistSize: watchlist.length,
          performers: topPerformers,
          disclaimer: results.disclaimer,
        }, null, 2),
      }],
    };
  }
);

// ============================================================
// Tool: worst_performers
// ============================================================
server.tool(
  "worst_performers",
  "Get worst N performing stocks from a watchlist, sorted by composite score ascending.",
  {
    symbols: {
      type: "array",
      items: { type: "string" },
      description: "Array of stock tickers to analyze (defaults to built-in 25-stock watchlist)",
    },
    limit: {
      type: "number",
      description: "Number of worst performers to return (default: 5)",
    },
  },
  async ({ symbols, limit }) => {
    const watchlist = (symbols && symbols.length > 0) ? symbols.filter(isValidSymbol) : DEFAULT_WATCHLIST;
    const count = Math.min(limit || 5, 25);

    const stockDataList = await fetchMultipleStocks(watchlist);
    const results = analyzePortfolio(stockDataList);
    // Rankings are sorted descending, so worst are at the end
    const worstPerformers = results.rankings.slice(-count).reverse();

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          analyzedAt: results.analyzedAt,
          worstN: count,
          watchlistSize: watchlist.length,
          performers: worstPerformers,
          disclaimer: results.disclaimer,
        }, null, 2),
      }],
    };
  }
);

// ============================================================
// Tool: market_overview
// ============================================================
server.tool(
  "market_overview",
  "Get overall market sentiment including average BDE score, breadth indicators, top/worst performers, and signal distribution.",
  {
    symbols: {
      type: "array",
      items: { type: "string" },
      description: "Array of stock tickers to analyze (defaults to built-in 25-stock watchlist)",
    },
  },
  async ({ symbols }) => {
    const watchlist = (symbols && symbols.length > 0) ? symbols.filter(isValidSymbol) : DEFAULT_WATCHLIST;

    const stockDataList = await fetchMultipleStocks(watchlist);
    const results = analyzePortfolio(stockDataList);
    const sentiment = getMarketSentiment(results.rankings);

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          ...sentiment,
          totalAnalyzed: results.totalStocks,
          bullishCount: results.bullish,
          neutralCount: results.neutral,
          bearishCount: results.bearish,
          disclaimer: results.disclaimer,
        }, null, 2),
      }],
    };
  }
);

// ============================================================
// Start server
// ============================================================
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("BDE Score MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
