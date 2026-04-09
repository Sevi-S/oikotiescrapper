#!/bin/bash
cd "$(dirname "$0")"
docker compose --profile scrape run --rm scraper
