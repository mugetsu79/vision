Architecture & Implementation Design: Traffic Monitor V21. Project Overview & Directives for the AI CoderContext: We are upgrading a V1 traffic counting prototype to a professional-grade V2 application. This version acts as a Dynamic Vision Agent (LLM-driven tracking) and a Centralized Video Management System (VMS).Commercial Feature: The system must support hybrid deployment modes. Cameras can either be processed centrally (RTSP streaming to a cloud server) or on the edge (remote Jetson node processing locally and pushing lightweight JSON to the server).Goal for AI Coder: Use this document as your blueprint to rewrite the application. Write clean, modular, highly concurrent Python code for the backend, and a modern React application for the frontend.Core Upgrades:Hybrid Inference Pipeline: Support both "Centralized" (pulling RTSP locally) and "Edge" (receiving JSON payloads via API) processing modes.Multi-Site & Multi-Camera Scaling: A centralized backend that manages parallel inference processes.LLM-Driven Dynamic Tracking: Natural language integration to switch tracking targets dynamically.Dynamic Historical Data & Export: A normalized database schema for Chart.js visualizations and CSV exports.AI Model: YOLO11 via ONNX Runtime for hardware portability.Tracking: ByteTrack for occlusion handling.Advanced Pre-processing: WDR for sun glare, Homography for speed, and CLAHE for night vision.2. System ArchitectureThe system uses a flexible Parent-Child architecture:Process A (FastAPI Master Node): Serves the React frontend, manages the SQLite database, handles LLM queries, and broadcasts WebSocket telemetry.If a camera is configured as central, it spawns Process B locally.If a camera is configured as edge, it exposes an ingestion API to receive data from a remote Process B over a VPN/Tunnel.Process B (Inference Engine Worker): Connects to the RTSP stream, runs YOLO inference, calculates speed, and filters targets.If running locally, it pushes metadata to a multiprocessing.Queue.If running on an edge device, it posts metadata to the Master Node's ingestion API.3. Module Specifications3.1. Database Schema (SQLite)sites Table: id, name, description.cameras Table: id, site_id, name, rtsp_url, processing_mode (enum: 'edge' or 'central'), and 8 Homography calibration coordinates.tracking_events Table: id, timestamp, camera_id, class_name (e.g., 'car', 'bus', 'person'), speed.3.2. Camera Pipeline & Image ProcessingJetson Orin Pipeline: If MIPI CSI, use nvarguscamerasrc. If RTSP, use nvv4l2decoder for hardware decoding.x86 Fallback Pipeline: Use standard cv2.VideoCapture.CPU Throttle: Implement FRAME_SKIP logic to prevent CPU bottlenecking.3.3. Inference (YOLO) & Dynamic Class FilteringModel: YOLO11 (yolo11n.onnx).Dynamic Filtering: Inference workers check a shared variable or API for active_classes. Unwanted classes are dropped before tracking.Execution Providers: Prioritize TensorrtExecutionProvider -> CUDAExecutionProvider -> OpenVINOExecutionProvider -> CPUExecutionProvider.3.4. Speed Measurement (Homography)Calculate H = cv2.getPerspectiveTransform(src_points, dst_points). Apply cv2.perspectiveTransform to the bottom-center of tracked bounding boxes to derive speed in real-world metrics.3.5. Backend (FastAPI & Master Node)Endpoints:GET /api/sites & POST /api/cameras: CRUD endpoints.GET /video_feed/{camera_id}: MJPEG stream.POST /api/edge/telemetry: [NEW] Ingestion webhook for remote Edge nodes to post their JSON tracking data and frame updates.WS /ws/telemetry: Broadcasts JSON metadata for all cameras to the React frontend.POST /api/query: LLM integration to update active_classes.GET /api/history & GET /api/export: Historical aggregations and CSV downloads.3.6. Frontend (React + Tailwind CSS)Multi-Site Dashboard: Grid layout of VideoStream components.Settings Panel: CRUD interface. Must include a toggle for "Processing Mode: Central Server vs. Edge Node".Dynamic Stats Cards: Generate stat cards automatically based on keys found in the WebSocket counts object.LLM Query Bar: Chat input for natural language reconfiguration.History Page: Dynamic Chart.js graph and CSV export.4. Suggested Folder Structure/traffic_monitor_v2
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application, CRUD routes, Process Manager
│   │   ├── engine.py            # Multiprocessing Inference Worker (supports API pushing)
│   │   ├── camera.py            # Hardware-aware VideoCapture
│   │   ├── tracker.py           # YOLO inference, dynamic class filtering, ByteTrack
│   │   ├── speed_calc.py        # Homography math
│   │   └── llm_agent.py         # Parses user text into target classes
│   ├── models/
│   │   └── yolo11n.onnx         
│   ├── data/
│   │   └── config.db            
│   ├── requirements.txt
│   └── Dockerfile               
└── frontend/
    ├── package.json
    ├── tailwind.config.js       
    ├── vite.config.js
    └── src/
        ├── App.jsx              
        ├── pages/
        │   ├── Dashboard.jsx    
        │   ├── History.jsx      
        │   └── Settings.jsx     
        ├── components/
        │   ├── VideoStream.jsx  
        │   ├── DynamicStats.jsx 
        │   └── AgentInput.jsx   
        └── index.css            
