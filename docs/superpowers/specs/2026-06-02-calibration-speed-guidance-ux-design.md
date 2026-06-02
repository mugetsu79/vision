# Calibration And Speed Guidance UX Design

Date: 2026-06-02
Status: Proposed

## Product Goal

Make camera calibration understandable for an operator who is setting up a
scene in the product, not reading a computer-vision manual. The UI should make
three things obvious:

1. Calibration points are saved only when the calibration is complete.
2. Source and destination points are the same real-world marks viewed from two
   different perspectives.
3. Accurate speed measurements require a measured distance on the same flat
   plane where tracked objects move.

## Problem

During initial camera creation, the operator can add calibration points before
the camera has a captured frame. When the operator starts calibration but leaves
it incomplete, the backend cannot store it as a homography because the contract
requires exactly four source points, four destination points, and a positive
reference distance. The old UI allowed the operator to continue, so the partial
points were silently submitted as no calibration and disappeared on edit.

The copy also still asks operators to understand terms such as source points,
destination points, and reference distance without enough plain-language
guidance about how to pick good marks, why point order matters, and how to
calibrate for speed.

## UX Principles

- Use simple terms first, then the technical term: "camera image points
  (source points)" and "top-down points (destination points)".
- Never silently discard started calibration work.
- Tell the operator what to do next: complete the four points, add the measured
  distance, refresh the still, or clear calibration.
- Keep advanced geometry detail available, but make the happy path scannable.
- Explain speed accuracy as a checklist, not as a paragraph.

## Scope

In scope:

- Plain-language calibration descriptions in the camera wizard.
- A dedicated speed calibration guide in the Calibration step.
- Clear warnings when the operator is using the provisional authoring plane
  before a real frame capture exists.
- Readiness states that distinguish:
  - no calibration started
  - calibration draft started but incomplete
  - calibration complete and saved
  - frame capture needed for alignment review
- Tests for partial calibration blocking and speed guidance copy.

Out of scope:

- Changing the backend homography schema.
- Saving partial homography drafts server-side.
- Reworking the geometry canvas interaction model.
- Automatic speed calibration from video.

## Required Behavior

### Partial Calibration

If any source point, destination point, or reference distance has been entered,
the operator must not be allowed to leave Calibration or save the camera until
the homography is complete.

The UI should say:

- how many source points are present out of four
- how many destination points are present out of four
- whether the measured reference distance is missing
- that the operator can clear the calibration if they do not want to save it

### Initial Create Without Frame Capture

When creating a new camera, the Calibration step may use a provisional
authoring plane because the camera is not saved yet and no setup still can be
captured.

The UI should say:

- "This is a temporary drawing plane until the camera is saved."
- "After saving, edit the camera and refresh the still to confirm the points
  still line up with the real video frame."
- "Complete calibration before saving if you want these points preserved."

### Plain-Language Geometry

Source points:

- "Click four fixed marks on the camera image."
- Good examples: floor corners, lane marks, doorway corners, loading-bay paint.
- Bad examples: shadows, people, vehicles, wall corners above the floor, moved
  objects.

Destination points:

- "Draw the same four marks as if looking straight down from above."
- "Use the same order as the camera-image points."
- "The destination drawing does not need GPS coordinates."

Reference distance:

- "Measure a real distance between two visible marks, in meters."
- "Use a longer measured span when possible; it usually gives better speed
  estimates than a short guessed distance."

### Speed Accuracy Guide

Add a compact speed checklist:

- Camera is fixed and not zooming.
- The four source points are on the same flat ground plane where people or
  vehicles move.
- Destination points match the same marks in the same order.
- Reference distance is measured in meters, not guessed.
- The measured distance is on the same plane as the tracked feet/wheels.
- Objects used for speed testing move through the calibrated area, not outside
  it.
- Operator has tested with a known walk, cart, or vehicle speed and adjusted
  calibration if the result is off.

Speed warning copy:

"Speed is only as accurate as the calibration plane. If objects move on a ramp,
stairs, raised platform, or outside the marked area, treat speed as an estimate."

## Acceptance Criteria

- Started but incomplete calibration cannot be silently discarded.
- The Calibration step explains source points, destination points, point order,
  provisional frame setup, reference distance, and speed readiness in plain
  language.
- Speed guidance explicitly tells operators how to choose measured marks and
  validate the result.
- Tests protect the partial-calibration blocking behavior and key speed
  guidance text.
