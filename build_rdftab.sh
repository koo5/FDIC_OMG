#!/bin/bash
# Build rdftab viewer
# This builds directly to fdic_omg/viewer_template as configured in vite.config.viewer.js
npm --prefix ../../../rdftab run build:viewer

echo "✓ Built viewer template in fdic_omg/viewer_template"