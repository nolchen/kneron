#!/usr/bin/env bash
# Program-view API (projects, roadmap, priorities, AI summary, graph).
. "$(dirname "$0")/_common.sh"

echo "### GET /api/projects — projects/repos"
req GET /api/projects

echo "### GET /api/roadmap — milestones / timeline"
req GET /api/roadmap

echo "### GET /api/priorities — ranked priorities"
req GET /api/priorities

echo "### GET /api/summary — AI executive summary (slower)"
req GET /api/summary

echo "### GET /api/graph — knowledge-graph nodes + edges"
req GET /api/graph
