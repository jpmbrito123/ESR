# Over-the-Top (OTT) Multimedia Delivery Service

This project consists of developing a prototype for an Over-the-Top (OTT) multimedia delivery system, using the CORE emulator as a testbed. The goal is to build an application-level overlay network capable of delivering real-time audio, video and text streams from a content server to multiple clients efficiently.

## Project Overview

The implementation was carried out in several phases, addressing core components of multimedia streaming systems, including initial setup, overlay network construction, content delivery, monitoring and fault tolerance.

## Key Features

### 1. Initial Setup and Test Environment

- Selected the programming language for the implementation.
- Designed and configured the network topology using the CORE emulator.
- Defined the transport protocol (TCP/UDP) based on system requirements.
- Built a basic client-server application for testing connectivity.

### 2. Overlay Network Construction (Shared Tree)

- Developed an overlay node (`oNode`) capable of acting as both a client and a server.
- Implemented message transmission and reception for overlay communication.
- Designed and deployed overlay construction strategies.
- Maintained persistent connections between Rendezvous Points (RP) and servers.

### 3. Multimedia Streaming Service

- Implemented a streaming service based on provided examples.
- Adapted the system for real-time video transmission and playback.
- Incorporated different codecs and video files for compatibility testing.

### 4. Content Server Monitoring

- Implemented heartbeat messages between the RP and servers.
- Defined and used metrics to dynamically select the most suitable server for each client.

### 5. Optimized Content Delivery

- Built intelligent data flows to reduce network overhead.
- Developed traffic management strategies for stream delivery across the overlay.

### 6. Fault Recovery and Node Management

- Introduced fault tolerance mechanisms for overlay disconnection and recovery.
- Added support for seamless integration of new nodes into the overlay network.

## Technologies

- Language: Python (mainly used)
- Network Emulator: [CORE](https://www.nrl.navy.mil/itd/ncs/products/core)
- Protocols: TCP, UDP
- Multimedia: ffmpeg, VLC, video codecs

