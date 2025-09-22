#!/bin/bash
uvicorn novars2:app --host 0.0.0.0 --port $PORT
