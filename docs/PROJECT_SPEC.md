# Project Specification: AI + Programming Contest Training System

> Source: Program Design Contest Combined with AI Student Training System Project Description (2025-04-24)
> Original file: `程序设计竞赛结合AI的学生培训系统项目说明.pdf`

---

## 1. Project Information

| Field | Value |
|-------|-------|
| Project Name | AI + Programming Contest Training System |
| Domain | Artificial Intelligence, Education Technology, Software Engineering |
| Type | Applied Research & Platform Development |
| Duration | 12 months |
| Start Date | 2025-04-24 |

---

## 2. Background and Significance

Programming contests (ACM-ICPC, NOIP, etc.) are important platforms for cultivating and selecting computer science talent. However, traditional contest training has the following problems:

1. Uneven distribution of teaching resources; high-quality instructors are scarce
2. Large individual differences among students; difficult to provide personalized guidance
3. Steep learning curve; beginners easily experience frustration
4. Lagging evaluation and feedback mechanisms; hard to correct learning misconceptions in time
5. Lack of proactive learning guidance; students' autonomous learning ability development is limited

The development of AI technology provides new approaches to solve the above problems. AI can analyze student learning behavior, provide personalized guidance, automatically evaluate code quality, and even simulate different problem-solving approaches. In particular, the rise of AI agent technology enables systems to interact with students in a more proactive and intelligent way, providing personalized tutoring.

This project aims to integrate AI technology into programming contest training, building an intelligent, personalized, and efficient training system to improve students' learning outcomes and contest performance.

---

## 3. Research Content and Goals

### Research Content

1. **Contest Knowledge Graph Construction**: Analyze the knowledge point distribution of mainstream programming contests and construct a structured knowledge graph
2. **Learning Path Intelligent Planning**: Generate personalized learning paths based on students' existing knowledge foundation and learning goals
3. **AI Code Analysis and Feedback**: Automatically analyze student code, identify problems, and provide improvement suggestions
4. **Intelligent Problem Recommendation System**: Recommend suitable practice problems based on students' ability level and learning progress
5. **Programming Thinking Visualization**: Transform abstract algorithmic thinking processes into visual expressions to improve understanding efficiency
6. **Virtual Teaching Assistant System**: Build a virtual teaching assistant based on large language models, providing real-time Q&A and guidance
7. **Multi-function AI Agent Design**:
   - Learning Partner Agent: Accompany students' learning process, provide emotional support and learning motivation
   - Contest Coach Agent: Simulate contest environment, provide professional guidance and strategy suggestions
   - Code Review Agent: Focus on code quality analysis, provide optimization suggestions
   - Problem Analysis Agent: Deeply analyze contest problems, guide students to think about problem-solving approaches
   - Learning Management Agent: Monitor learning progress, provide time management suggestions

### Expected Goals

1. Develop a complete AI-assisted programming contest training system
2. Construct a knowledge graph and problem bank covering mainstream contests (no less than 3000 problems)
3. Achieve code analysis and feedback functionality with no less than 85% accuracy
4. After system use, improve student problem-solving efficiency by 30%+, contest scores by 20%+
5. Form a replicable AI-assisted programming education model, and promote application on and off campus
6. Develop 5+ specialized AI Agents to address different needs in contest training

---

## 4. Technical Roadmap and Methods

### 4.1 Data Collection and Preprocessing

- Collect and organize mainstream contest problem banks and solution data
- Collect student programming behavior and learning trajectory data
- Build programming ability assessment model
- Construct contest coach knowledge base and teaching strategy dataset

### 4.2 Core Algorithm R&D

- Code understanding and generation based on large language models (e.g., DeepSeek V3)
- Knowledge graph construction and reasoning
- Personalized recommendation algorithm design
- Programming thinking visualization algorithm R&D
- Multi-agent collaboration framework design
- Agent behavior strategy and decision model

### 4.3 AI Agent Architecture Design

- Agent role definition and specialized training
- Agent-student interaction mechanism design
- Multi-agent collaborative work mechanism
- Agent knowledge update and self-improvement mechanism
- Agent behavior interpretability design

### 4.4 System Architecture Design

- Frontend: Vue framework for building responsive interface
- Backend: Microservice architecture, FastAPI/Django framework
- Database: MongoDB (unstructured data) + MySQL (relational data)
- Agent cluster management and scheduling system

> **Implementation Note**: The current system uses PostgreSQL for both structured and semi-structured data (via the ai_agent schema), and QDUOJ's Django backend for the OJ subsystem. MongoDB is not currently deployed. The architecture may evolve toward the spec's MongoDB + MySQL design in later phases.

### 4.5 Evaluation and Optimization

- A/B testing for different algorithm effectiveness
- User feedback collection and analysis
- System performance optimization and scaling
- Agent behavior evaluation and optimization

---

## 5. Innovation Points

1. **Multi-modal Programming Learning**: Combine text, images, video and other multi-modal data to comprehensively present programming knowledge
2. **Programming Thinking Visualization**: Transform abstract algorithms into intuitive visual expressions, lowering understanding barriers
3. **Intelligent Evaluation and Feedback**: Not only judge code correctness, but also evaluate code quality, efficiency, and style
4. **Adaptive Learning Path**: Dynamically adjust learning paths based on learning outcomes, achieving truly personalized learning
5. **Collaborative Learning Ecology**: Build a collaborative learning ecosystem of students, teachers, and AI
6. **Specialized AI Agent Team**: Different role agents work collaboratively to meet learners' multi-faceted needs
7. **Proactive Learning Guidance**: Agents can proactively sense learning status and provide timely help and guidance
8. **Emotional Intelligence Interaction**: Agents have emotion recognition capability, adjusting interaction strategy based on student emotion
9. **Contest Scenario Simulation**: Agents can simulate real contest environment and pressure, improving students' coping ability

---

## 6. Expected Outcomes and Application Prospects

### Expected Outcomes

1. A complete AI-assisted programming contest training system
2. Contest knowledge graph and intelligent problem bank system
3. Programming ability assessment and learning path planning model
4. AI Agent collaboration framework and its application method in education
5. Agent-based personalized learning model and method

### Application Prospects

1. **Campus Promotion**: First promote and use in computer science related majors, improving student contest scores
2. **Regional Radiation**: Promote to surrounding universities and middle schools, improving regional informatics contest levels
3. **Commercialization Potential**: Collaborate with education technology enterprises to develop commercial versions serving a broader programming learning population
4. **Model Promotion**: Promote the AI-assisted learning model to other discipline contest training
5. **Agent Technology Expansion**: Expand the developed Agent framework to other education scenarios

---

## 7. Project Features and Highlights

1. **Interdisciplinary Integration**: Combines AI, education, cognitive science, and software engineering
2. **Research-Practice Integration**: Directly apply latest research results to teaching practice, forming a virtuous cycle
3. **Continuous Iterative Upgrade**: Continuously optimize the system based on user data and feedback, maintaining technological advancement
4. **Open Ecology Construction**: Build open API interfaces, allowing third-party plugin and extension development
5. **Data-Driven Decision Making**: Utilize teaching big data generated by the system to support educational decision-making
6. **Multi-Agent Collaborative System**: Specialized agents work collaboratively, providing comprehensive learning support
7. **Human-Machine Collaboration Enhancement**: AI does not replace teachers, but enhances teacher capabilities and optimizes resource allocation
8. **Intelligent Interaction Experience**: Intelligent interaction based on affective computing, providing personalized learning experience

---

## 8. Implementation Status (Current vs. Spec)

| Spec Goal | Current Status | Gap |
|-----------|---------------|-----|
| 5 specialized AI Agents | 5 Worker Agents implemented (CodeReviewer, ProblemAnalyzer, ContestCoach, LearningPartner, LearningManager) | Agents work but lack specialized training; routing is intent-based only |
| Knowledge graph + 3000 problems | 609 problems imported (FPS), 19 tags | Need 2400+ more problems; no structured knowledge graph yet |
| 85% code analysis accuracy | LLM-powered review works conversationally | No structured evaluation; accuracy not measured |
| 30% efficiency improvement | Not measured | No baseline or tracking system |
| Personalized learning path | LearningManager Agent exists | No actual path planning algorithm |
| Contest simulation mode | Not implemented | Planned for Phase 4 |
| Emotional intelligence | Keyword-based emotion analysis (OPT-009) | Need sentiment model upgrade |
| Programming thinking visualization | Not implemented | Planned for Phase 4 |
| Open API for extensions | AI Agent has WebSocket API | No formal extension/plugin system |
| Multi-modal learning | Text-only currently | No image/video integration |

---

## 9. Alignment with Development Roadmap

| Project Phase | Spec Coverage |
|---------------|--------------|
| Phase 1: Foundation (done) | System deployment, problem bank, basic AI chat |
| Phase 2: Stability (done) | Persistence, identity binding, error handling |
| Phase 3: Intelligence (in progress) | Code analysis, scope guard, structured output, streaming |
| Phase 4: Knowledge & Intelligence (planned) | Knowledge graph, learning path, visualization, emotional AI |
| Phase 5: Scale & Evaluation (planned) | A/B testing, performance evaluation, promotion |

---

*Document generated from the official project specification PDF dated 2025-04-24.*
*For the current development status, see [README.md](../README.md) and [docs/README.md](README.md).*
