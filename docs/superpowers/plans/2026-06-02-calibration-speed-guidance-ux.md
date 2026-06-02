# Calibration And Speed Guidance UX Implementation Plan

Date: 2026-06-02
Status: Proposed

## Goal

Improve the Camera Wizard Calibration step so operators understand how to set
source/destination points and how to calibrate accurately for speed, while
preventing started calibration work from being silently lost.

## Task 1: Preserve-Or-Block Calibration Drafts

Files:

- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/cameras/CameraWizard.test.tsx`

Steps:

- Add a helper that detects whether calibration has started when any source
  point, destination point, or reference distance exists.
- If calibration has started, require four source points, four destination
  points, and a positive reference distance before leaving Calibration.
- Keep untouched calibration allowed for detection-only scenes.
- Add a regression test for creating a camera, adding partial source and
  destination points, and attempting to continue.

## Task 2: Rewrite Calibration Copy In Plain Language

Files:

- `frontend/src/components/cameras/scene-guidance.ts`
- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/cameras/HomographyEditor.tsx`

Steps:

- Replace technical-first text with operator-first text.
- Explain "camera image points (source points)" and "top-down points
  (destination points)" consistently.
- Add concrete examples of good and bad point choices.
- Make provisional-plane copy explicit during initial create.
- Keep expanded details available but make the default hints shorter.

## Task 3: Add Speed Calibration Guide

Files:

- `frontend/src/components/cameras/scene-guidance.ts`
- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/guidance/ReadinessChecklist.tsx` if needed
- `frontend/src/components/cameras/CameraWizard.test.tsx`

Steps:

- Add a "Speed accuracy" guidance section in Calibration.
- Show a checklist for fixed camera, flat plane, four matching points,
  measured distance, same-plane object motion, and known-speed validation.
- Add warning copy for ramps, stairs, raised platforms, zoom changes, and
  movement outside the calibrated area.
- Test that the speed guidance appears in Calibration.

## Task 4: Improve Readiness States

Files:

- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/cameras/HomographyEditor.tsx`

Steps:

- Add readiness labels for:
  - not started
  - draft started
  - missing source points
  - missing destination points
  - missing measured distance
  - complete
  - refresh still after save
- Make the primary validation message match the readiness row that is blocking
  save.
- Keep the existing payload behavior: send `homography` only when complete.

## Task 5: Validation

Run:

```bash
corepack pnpm --dir frontend test src/components/cameras/CameraWizard.test.tsx
corepack pnpm --dir frontend build
```

Expected:

- CameraWizard tests pass.
- Frontend build passes.
- No backend schema or runtime behavior changes.
