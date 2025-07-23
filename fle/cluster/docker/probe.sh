#!/bin/bash
if nc -zu 127.0.0.1 34197; then
  exit 0
else
  exit 1
fi