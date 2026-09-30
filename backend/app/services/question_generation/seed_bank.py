from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import QuestionItem, AudioAsset, WritingPrompt
from app.services.question_generation.validator import compute_content_hash, validate_question_item
from app.services.tts.tts_engine import tts_engine


def get_initial_reading_items() -> List[Dict[str, Any]]:
    """
    Original Reading question bank covering all 9 CEST General Reading task types (RT-01 to RT-09)
    across CEFR levels A1 to C1 (PRD Section 10.2 & 20.3).
    """
    return [
        # ---------------- RT-01: Open Cloze (5 gaps each) ----------------
        {
            "skill": "reading",
            "task_type": "RT-01",
            "cefr_target": "A2",
            "difficulty_theta": -0.75,
            "primary_topic": "daily_routines",
            "scenario": "weekend plans",
            "cognitive_focus": ["grammar", "syntactic_parsing"],
            "explanation": "Gap 1 requires preposition 'on' before days of the week; Gap 2 requires 'with' for accompaniment; Gap 3 requires 'because' for reason; Gap 4 requires 'a' before singular countable noun; Gap 5 requires 'to' after 'going'.",
            "content_json": {
                "type": "open_cloze",
                "title": "My Saturday Morning Routine",
                "instructions": "Read the short text below and type ONE grammatical word for each gap (1–5).",
                "text_segments": [
                    {"text": "I usually wake up early "},
                    {"gap_id": "g1", "number": 1},
                    {"text": " Saturdays because I enjoy walking in the neighbourhood park. I often go there "},
                    {"gap_id": "g2", "number": 2},
                    {"text": " my younger brother. We prefer the morning hours "},
                    {"gap_id": "g3", "number": 3},
                    {"text": " the paths are quiet and cool. After our walk, we always buy "},
                    {"gap_id": "g4", "number": 4},
                    {"text": " cup of hot chocolate from the corner bakery before going back "},
                    {"gap_id": "g5", "number": 5},
                    {"text": " our apartment."},
                ],
                "gaps": [
                    {"id": "g1", "accepted_answers": ["on"], "primary_answer": "on", "answer_type": "single_word"},
                    {"id": "g2", "accepted_answers": ["with"], "primary_answer": "with", "answer_type": "single_word"},
                    {"id": "g3", "accepted_answers": ["because", "as", "since", "when"], "primary_answer": "because", "answer_type": "single_word"},
                    {"id": "g4", "accepted_answers": ["a", "one"], "primary_answer": "a", "answer_type": "single_word"},
                    {"id": "g5", "accepted_answers": ["to"], "primary_answer": "to", "answer_type": "single_word"},
                ],
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-01",
            "cefr_target": "B1",
            "difficulty_theta": 0.05,
            "primary_topic": "workplace",
            "scenario": "remote working",
            "cognitive_focus": ["grammar", "syntactic_parsing", "cohesion"],
            "explanation": "1: 'have' (present perfect auxiliary); 2: 'instead' (instead of); 3: 'which' (relative pronoun referring to flexibility); 4: 'more' (comparative); 5: 'unless' or 'if' conditional connector.",
            "content_json": {
                "type": "open_cloze",
                "title": "Working from a Community Hub",
                "instructions": "Complete the text below by typing ONE suitable grammatical word in each gap (1–5).",
                "text_segments": [
                    {"text": "Over the past two years, many office employees "},
                    {"gap_id": "g1", "number": 1},
                    {"text": " chosen to work from small neighbourhood co-working hubs "},
                    {"gap_id": "g2", "number": 2},
                    {"text": " of commuting to the city centre every day. This arrangement offers a balanced routine, "},
                    {"gap_id": "g3", "number": 3},
                    {"text": " helps staff separate home life from professional duties. Many managers also report that teams are "},
                    {"gap_id": "g4", "number": 4},
                    {"text": " focused during shorter meetings, provided everyone agrees on clear weekly goals "},
                    {"gap_id": "g5", "number": 5},
                    {"text": " the project begins."},
                ],
                "gaps": [
                    {"id": "g1", "accepted_answers": ["have"], "primary_answer": "have", "answer_type": "single_word"},
                    {"id": "g2", "accepted_answers": ["instead"], "primary_answer": "instead", "answer_type": "single_word"},
                    {"id": "g3", "accepted_answers": ["which", "that"], "primary_answer": "which", "answer_type": "single_word"},
                    {"id": "g4", "accepted_answers": ["more", "very", "better"], "primary_answer": "more", "answer_type": "single_word"},
                    {"id": "g5", "accepted_answers": ["before", "when", "once"], "primary_answer": "before", "answer_type": "single_word"},
                ],
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-01",
            "cefr_target": "B2",
            "difficulty_theta": 0.82,
            "primary_topic": "science_environment",
            "scenario": "urban architecture",
            "cognitive_focus": ["grammar", "syntactic_parsing", "discourse_markers"],
            "explanation": "1: 'not' (not only... but also); 2: 'by' (passive/method preposition); 3: 'such' (such as); 4: 'Despite' or 'Notwithstanding'; 5: 'be' (modal passive 'can be reduced').",
            "content_json": {
                "type": "open_cloze",
                "title": "Passive Cooling in Modern Buildings",
                "instructions": "Type ONE word in each gap (1–5) to complete the article extract.",
                "text_segments": [
                    {"text": "Architects designing public libraries in warm climates are "},
                    {"gap_id": "g1", "number": 1},
                    {"text": " only rethinking window placement, but also reviving traditional ventilation towers. Indoor temperatures are regulated naturally "},
                    {"gap_id": "g2", "number": 2},
                    {"text": " directing cool night air through thermal stone floors. Materials "},
                    {"gap_id": "g3", "number": 3},
                    {"text": " as compressed earth blocks absorb heat slowly throughout the afternoon. "},
                    {"gap_id": "g4", "number": 4},
                    {"text": " higher initial design costs, annual electricity consumption can "},
                    {"gap_id": "g5", "number": 5},
                    {"text": " reduced by nearly forty percent."},
                ],
                "gaps": [
                    {"id": "g1", "accepted_answers": ["not"], "primary_answer": "not", "answer_type": "single_word"},
                    {"id": "g2", "accepted_answers": ["by"], "primary_answer": "by", "answer_type": "single_word"},
                    {"id": "g3", "accepted_answers": ["such"], "primary_answer": "such", "answer_type": "single_word"},
                    {"id": "g4", "accepted_answers": ["despite"], "primary_answer": "despite", "answer_type": "single_word"},
                    {"id": "g5", "accepted_answers": ["be"], "primary_answer": "be", "answer_type": "single_word"},
                ],
            },
        },

        # ---------------- RT-02: Multiple-choice Cloze (5 gaps each) ----------------
        {
            "skill": "reading",
            "task_type": "RT-02",
            "cefr_target": "A2",
            "difficulty_theta": -0.65,
            "primary_topic": "travel",
            "scenario": "train journey",
            "cognitive_focus": ["lexical_access", "collocation"],
            "explanation": "1: 'platform' (trains depart from a platform); 2: 'comfortable' (describes seats); 3: 'scenery' (views outside the window); 4: 'arrived' (arrived at the station); 5: 'borrow' (take a map temporarily).",
            "content_json": {
                "type": "mcq_cloze",
                "title": "A Coastal Train Trip",
                "instructions": "Read the text below and choose the best word (A, B or C) for each gap (1–5).",
                "passage": "Last Sunday, Clara took the early express train to the coast. She checked the information board and walked quickly to (1) ____ four. Inside the carriage, she found a very (2) ____ window seat with a small table. During the two-hour ride, she enjoyed watching the green hills and coastal (3) ____ pass by. When the train (4) ____ at the harbour station, she stopped at the visitor desk to (5) ____ a cycling map for the afternoon.",
                "gaps": [
                    {
                        "id": "g1",
                        "number": 1,
                        "options": [
                            {"id": "A", "text": "platform"},
                            {"id": "B", "text": "pavement"},
                            {"id": "C", "text": "corridor"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g2",
                        "number": 2,
                        "options": [
                            {"id": "A", "text": "comfortable"},
                            {"id": "B", "text": "convenient"},
                            {"id": "C", "text": "confident"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g3",
                        "number": 3,
                        "options": [
                            {"id": "A", "text": "scenery"},
                            {"id": "B", "text": "curtain"},
                            {"id": "C", "text": "display"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g4",
                        "number": 4,
                        "options": [
                            {"id": "A", "text": "reached"},
                            {"id": "B", "text": "arrived"},
                            {"id": "C", "text": "entered"},
                        ],
                        "correct_option_id": "B",
                    },
                    {
                        "id": "g5",
                        "number": 5,
                        "options": [
                            {"id": "A", "text": "collect"},
                            {"id": "B", "text": "lend"},
                            {"id": "C", "text": "remind"},
                        ],
                        "correct_option_id": "A",
                    },
                ],
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-02",
            "cefr_target": "B2",
            "difficulty_theta": 0.70,
            "primary_topic": "technology",
            "scenario": "digital repair cafes",
            "cognitive_focus": ["lexical_access", "collocation", "register"],
            "explanation": "1: 'discarding' (throwing away); 2: 'guidance' (under the guidance of); 3: 'extend' (extend the lifespan); 4: 'reluctant' (hesitant/unwilling); 5: 'fosters' (encourages/promotes).",
            "content_json": {
                "type": "mcq_cloze",
                "title": "Neighborhood Repair Workshops",
                "instructions": "Read the text and select the correct word (A, B, C or D) for each gap (1–5).",
                "passage": "Across many towns, volunteer-run repair workshops are encouraging residents to mend household appliances rather than (1) ____ them at the first sign of a fault. Visitors bring toasters, lamps, and laptops to community halls where retired engineers offer practical (2) ____ free of charge. The initiative aims not only to (3) ____ the working lifespan of everyday electronics, but also to demystify how modern devices are assembled. Although some consumers initially feel (4) ____ to open a broken appliance themselves, hands-on coaching quickly builds confidence and (5) ____ a stronger culture of resourcefulness.",
                "gaps": [
                    {
                        "id": "g1",
                        "number": 1,
                        "options": [
                            {"id": "A", "text": "discarding"},
                            {"id": "B", "text": "dismissing"},
                            {"id": "C", "text": "resigning"},
                            {"id": "D", "text": "releasing"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g2",
                        "number": 2,
                        "options": [
                            {"id": "A", "text": "guidance"},
                            {"id": "B", "text": "regulation"},
                            {"id": "C", "text": "conduct"},
                            {"id": "D", "text": "permission"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g3",
                        "number": 3,
                        "options": [
                            {"id": "A", "text": "widen"},
                            {"id": "B", "text": "extend"},
                            {"id": "C", "text": "spread"},
                            {"id": "D", "text": "stretch"},
                        ],
                        "correct_option_id": "B",
                    },
                    {
                        "id": "g4",
                        "number": 4,
                        "options": [
                            {"id": "A", "text": "reluctant"},
                            {"id": "B", "text": "remote"},
                            {"id": "C", "text": "adverse"},
                            {"id": "D", "text": "contrary"},
                        ],
                        "correct_option_id": "A",
                    },
                    {
                        "id": "g5",
                        "number": 5,
                        "options": [
                            {"id": "A", "text": "fosters"},
                            {"id": "B", "text": "compels"},
                            {"id": "C", "text": "enforces"},
                            {"id": "D", "text": "abides"},
                        ],
                        "correct_option_id": "A",
                    },
                ],
            },
        },

        # ---------------- RT-03: Cross Text Matching (4 texts, B2-C1) ----------------
        {
            "skill": "reading",
            "task_type": "RT-03",
            "cefr_target": "B2",
            "difficulty_theta": 0.95,
            "primary_topic": "education",
            "scenario": "university assessment methods",
            "cognitive_focus": ["cross_text_synthesis", "opinion_comparison", "inference"],
            "explanation": "Q1 -> B (Writer B shares Writer A's view that group projects mirror real workplaces); Q2 -> C (Writer C argues oral defences are too stressful and subjective); Q3 -> D (Writer D highlights portfolio flexibility across disciplines); Q4 -> A (Writer A warns about unequal workload distribution in teams).",
            "content_json": {
                "type": "cross_text_matching",
                "title": "Rethinking University Assessments",
                "instructions": "Read the four short texts (A–D) by university lecturers discussing assessment formats. For each question (1–4), choose the correct text (A, B, C or D).",
                "texts": [
                    {
                        "id": "A",
                        "author": "Dr. Helena Vance — Engineering",
                        "content": "Written examinations still have a place for verifying core analytical fluency, yet they rarely reflect how engineers actually solve problems. In professional practice, graduates collaborate across specialties. That is why collaborative design projects are indispensable, even if tutors must monitor teams carefully so that one diligent student does not end up carrying the entire workload for less committed peers.",
                    },
                    {
                        "id": "B",
                        "author": "Prof. Marcus Lind — Business Studies",
                        "content": "Like Helena, I am convinced that team-based assignments prepare undergraduates far better for modern organisations than isolated three-hour exam halls ever could. However, rather than relying on tutor policing alone, we pair group reports with brief individual vivas. Ten minutes of targeted questioning immediately reveals whether a candidate genuinely grasps the financial model their group submitted.",
                    },
                    {
                        "id": "C",
                        "author": "Dr. Priya Nair — History",
                        "content": "Advocates of spoken questioning often overlook how much performance anxiety can distort a student's grade. A thoughtful historian may articulate nuanced arguments brilliantly in an extended research essay yet freeze when pressed on the spot by a panel. Timed unseen papers have flaws, certainly, but replacing them with oral interviews risks rewarding rhetorical confidence over deep scholarship.",
                    },
                    {
                        "id": "D",
                        "author": "Dr. Jonas Meyer — Media & Design",
                        "content": "The mistake lies in searching for a single universal assessment format. Instead of forcing every department into identical exam rules, cumulative portfolios allow students to submit iterative drafts, code repositories, or critical reflections over an entire semester. When learners review feedback between stages, assessment becomes part of the learning process rather than a final hurdle.",
                    },
                ],
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Which lecturer agrees with Dr. Vance (Text A) that collaborative tasks reflect real-world professional environments?",
                        "options": [{"id": "A", "text": "Text A"}, {"id": "B", "text": "Text B"}, {"id": "C", "text": "Text C"}, {"id": "D", "text": "Text D"}],
                        "correct_option_id": "B",
                        "explanation": "Prof. Lind (Text B) explicitly agrees with Helena that team-based assignments reflect modern organisations.",
                    },
                    {
                        "id": "q2",
                        "stem": "Which lecturer disagrees with Prof. Lind (Text B) regarding the fairness and reliability of spoken questioning?",
                        "options": [{"id": "A", "text": "Text A"}, {"id": "B", "text": "Text B"}, {"id": "C", "text": "Text C"}, {"id": "D", "text": "Text D"}],
                        "correct_option_id": "C",
                        "explanation": "Dr. Nair (Text C) argues that oral interviews risk rewarding rhetorical confidence and cause performance anxiety.",
                    },
                    {
                        "id": "q3",
                        "stem": "Which lecturer proposes continuous multi-stage submissions over a semester instead of one-off final tests?",
                        "options": [{"id": "A", "text": "Text A"}, {"id": "B", "text": "Text B"}, {"id": "C", "text": "Text C"}, {"id": "D", "text": "Text D"}],
                        "correct_option_id": "D",
                        "explanation": "Dr. Meyer (Text D) advocates cumulative portfolios with iterative drafts across the semester.",
                    },
                    {
                        "id": "q4",
                        "stem": "Which lecturer points out the risk of unfair effort distribution among students working together?",
                        "options": [{"id": "A", "text": "Text A"}, {"id": "B", "text": "Text B"}, {"id": "C", "text": "Text C"}, {"id": "D", "text": "Text D"}],
                        "correct_option_id": "A",
                        "explanation": "Dr. Vance (Text A) notes that tutors must monitor teams so one student does not carry the entire workload.",
                    },
                ],
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-03",
            "cefr_target": "C1",
            "difficulty_theta": 1.45,
            "primary_topic": "urban_policy",
            "scenario": "pedestrianisation of city centres",
            "cognitive_focus": ["cross_text_synthesis", "attitude", "inferencing"],
            "explanation": "Q1 -> C (Text C challenges Text A's claim that retail revenue inevitably drops); Q2 -> D (Text D critiques aesthetic gentrification without transit links); Q3 -> B (Text B focuses on delivery logistics); Q4 -> A (Text A worries about independent specialist shops).",
            "content_json": {
                "type": "cross_text_matching",
                "title": "Car-Free City Centres: Four Perspectives",
                "instructions": "Read the four extracts (A–D) discussing urban pedestrian zones and match each question (1–4) to the correct text.",
                "texts": [
                    {
                        "id": "A",
                        "author": "Extract A — Retail Association Briefing",
                        "content": "While transforming central avenues into landscaped plazas looks appealing in architectural renders, municipal planners frequently underestimate the commercial fragility of specialist independent retailers. Unlike cafés, stores selling bulky household goods rely on customers who drive in from outer suburbs. Abruptly removing kerbside access without phased compensation inevitably diverts trade toward out-of-town retail parks.",
                    },
                    {
                        "id": "B",
                        "author": "Extract B — Urban Logistics Analyst",
                        "content": "The debate around pedestrianisation is too often framed solely around private commuters, ignoring the complex freight ecosystem that keeps a city functioning. Pharmacies, restaurants, and print shops require predictable morning loading windows. Unless councils invest in consolidated micro-distribution hubs and electric cargo bays on the perimeter, delivery drivers are simply forced into congested side streets.",
                    },
                    {
                        "id": "C",
                        "author": "Extract C — Municipal Economist",
                        "content": "Empirical audits across twelve European cities directly contradict the gloomy forecasts of retail lobbies. Once footfall stabilises after the initial transition, ground-floor vacancy rates in pedestrianised quarters consistently fall below metropolitan averages. Shoppers linger longer when freed from traffic noise, though I concur with logistics specialists that perimeter freight consolidation is a prerequisite for success.",
                    },
                    {
                        "id": "D",
                        "author": "Extract D — Transport Sociologist",
                        "content": "Removing cars from historic squares achieves little if public transport fares remain prohibitive for lower-income residents on the urban periphery. Without affordable radial tram or bus corridors, car-free zones risk becoming curated leisure enclaves accessible primarily to affluent inner-city dwellers, displacing rather than resolving metropolitan emissions.",
                    },
                ],
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Which writer directly disputes Extract A's prediction regarding the long-term commercial impact on shops?",
                        "options": [{"id": "A", "text": "Extract A"}, {"id": "B", "text": "Extract B"}, {"id": "C", "text": "Extract C"}, {"id": "D", "text": "Extract D"}],
                        "correct_option_id": "C",
                        "explanation": "Extract C cites empirical audits contradicting retail lobby forecasts and showing lower vacancy rates.",
                    },
                    {
                        "id": "q2",
                        "stem": "Which writer shares Extract B's concern about managing commercial deliveries around the edge of the zone?",
                        "options": [{"id": "A", "text": "Extract A"}, {"id": "B", "text": "Extract B"}, {"id": "C", "text": "Extract C"}, {"id": "D", "text": "Extract D"}],
                        "correct_option_id": "C",
                        "explanation": "Extract C states 'I concur with logistics specialists that perimeter freight consolidation is a prerequisite'.",
                    },
                    {
                        "id": "q3",
                        "stem": "Which writer argues that pedestrian zones can deepen social inequality if public transit affordability is ignored?",
                        "options": [{"id": "A", "text": "Extract A"}, {"id": "B", "text": "Extract B"}, {"id": "C", "text": "Extract C"}, {"id": "D", "text": "Extract D"}],
                        "correct_option_id": "D",
                        "explanation": "Extract D highlights prohibitive transit fares excluding lower-income periphery residents.",
                    },
                    {
                        "id": "q4",
                        "stem": "Which writer distinguishes between hospitality venues and shops selling heavy items?",
                        "options": [{"id": "A", "text": "Extract A"}, {"id": "B", "text": "Extract B"}, {"id": "C", "text": "Extract C"}, {"id": "D", "text": "Extract D"}],
                        "correct_option_id": "A",
                        "explanation": "Extract A contrasts cafés with specialist stores selling bulky household goods.",
                    },
                ],
            },
        },

        # ---------------- RT-04: Discrete Cloze (1 gap sentence) ----------------
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "A1",
            "difficulty_theta": -1.55,
            "primary_topic": "shopping",
            "scenario": "supermarket",
            "cognitive_focus": ["lexical_access"],
            "explanation": "'closed' is the correct adjective: the supermarket is not open on Sunday evenings.",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "The supermarket near our house is ________ on Sunday evenings, so we buy bread on Saturday.",
                "options": [
                    {"id": "A", "text": "closed"},
                    {"id": "B", "text": "finished"},
                    {"id": "C", "text": "stopped"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "B1",
            "difficulty_theta": -0.10,
            "primary_topic": "workplace",
            "scenario": "meeting schedule",
            "cognitive_focus": ["lexical_access", "phrasal_verbs"],
            "explanation": "'put off' means to postpone an event to a later time.",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "Because two team members were delayed at the airport, the director decided to ________ the budget meeting until Thursday.",
                "options": [
                    {"id": "A", "text": "put off"},
                    {"id": "B", "text": "call for"},
                    {"id": "C", "text": "take over"},
                    {"id": "D", "text": "turn down"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "C1",
            "difficulty_theta": 1.35,
            "primary_topic": "business",
            "scenario": "policy review",
            "cognitive_focus": ["lexical_precision", "collocation"],
            "explanation": "'scrutiny' collocates naturally with 'came under intense scrutiny' meaning careful, critical examination.",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "The contractor's environmental impact figures came under intense ________ during the public inquiry.",
                "options": [
                    {"id": "A", "text": "scrutiny"},
                    {"id": "B", "text": "glimpse"},
                    {"id": "C", "text": "supervision"},
                    {"id": "D", "text": "observance"},
                ],
                "correct_option_id": "A",
            },
        },

        # ---------------- RT-05: Discrete with a Graphic (Notice / Email / Message) ----------------
        {
            "skill": "reading",
            "task_type": "RT-05",
            "cefr_target": "A1",
            "difficulty_theta": -1.40,
            "primary_topic": "community",
            "scenario": "swimming pool notice",
            "cognitive_focus": ["specific_information"],
            "explanation": "The notice states 'Lockers require a £1 coin (returned after use)', so visitors need a £1 coin for a locker.",
            "content_json": {
                "type": "discrete_graphic",
                "graphic": {
                    "graphic_type": "notice",
                    "header": "WESTSIDE SWIMMING POOL — VISITOR NOTICE",
                    "subtext": "Open Daily: 07:00 – 20:30",
                    "body": "• Please shower before entering the main pool.\n• Lockers require a £1 coin (returned after use).\n• Children under 8 must be accompanied by an adult.",
                    "footer": "Reception sells swim caps and goggles.",
                },
                "stem": "What do visitors need to use a locker at the swimming pool?",
                "options": [
                    {"id": "A", "text": "A £1 coin that they get back later"},
                    {"id": "B", "text": "A ticket from the reception desk"},
                    {"id": "C", "text": "A membership card for the pool"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-05",
            "cefr_target": "A2",
            "difficulty_theta": -0.55,
            "primary_topic": "study",
            "scenario": "student text message",
            "cognitive_focus": ["gist", "purpose"],
            "explanation": "Leo writes that he left his chemistry notebook in the café and asks Maya to pick it up since she is still on campus.",
            "content_json": {
                "type": "discrete_graphic",
                "graphic": {
                    "graphic_type": "message",
                    "header": "Text Message — From: Leo (14:15)",
                    "subtext": "To: Maya",
                    "body": "Hi Maya! Are you still near the campus café? I think I left my blue chemistry notebook on the corner table by the window. If you walk past before your 3 p.m. seminar, could you grab it for me? I'm already on the bus home.",
                    "footer": "Delivered",
                },
                "stem": "Why has Leo sent this message to Maya?",
                "options": [
                    {"id": "A", "text": "To ask her to collect something he forgot"},
                    {"id": "B", "text": "To invite her to meet him at the campus café"},
                    {"id": "C", "text": "To check what time her afternoon seminar starts"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-05",
            "cefr_target": "B1",
            "difficulty_theta": 0.20,
            "primary_topic": "workplace",
            "scenario": "IT maintenance email",
            "cognitive_focus": ["specific_information", "inference"],
            "explanation": "The email instructs staff working over the weekend to download required files to their laptops before Friday at 18:00.",
            "content_json": {
                "type": "discrete_graphic",
                "graphic": {
                    "graphic_type": "email",
                    "header": "Subject: Scheduled Server Upgrade — This Saturday",
                    "subtext": "From: IT Support Desk | To: All Staff",
                    "body": "Please note that the shared document drive (S: Drive) will be offline for essential security maintenance from Saturday 08:00 until Sunday 14:00. Email and calendar access will remain unaffected. Anyone planning to prepare client presentations over the weekend should save copies of needed spreadsheets onto their local laptop folder before leaving on Friday at 18:00.",
                    "footer": "IT Infrastructure Team",
                },
                "stem": "What are staff advised to do if they need shared spreadsheets this weekend?",
                "options": [
                    {"id": "A", "text": "Save the files onto their own computers before Friday evening"},
                    {"id": "B", "text": "Request temporary weekend access from the IT Support Desk"},
                    {"id": "C", "text": "Send the spreadsheets to clients via email before Saturday morning"},
                ],
                "correct_option_id": "A",
            },
        },

        # ---------------- RT-06: Gapped Text — Sentences (5 gaps, 8 options) ----------------
        {
            "skill": "reading",
            "task_type": "RT-06",
            "cefr_target": "B1",
            "difficulty_theta": 0.25,
            "primary_topic": "hobbies",
            "scenario": "rooftop beekeeping",
            "cognitive_focus": ["cohesion", "text_level_representation"],
            "explanation": "gap1 -> B (contrasts initial fear of city pollution with thriving hives); gap2 -> E (explains what bees forage on in parks); gap3 -> A (links safety training course to beginners); gap4 -> G (describes autumn honey harvest sharing); gap5 -> D (concludes with impact on how residents view nature).",
            "content_json": {
                "type": "gapped_text_sentences",
                "title": "Keeping Bees on City Rooftops",
                "instructions": "Five sentences have been removed from the article below. Choose from the sentences (A–H) the one which fits each gap (gap1–gap5). There are three extra sentences which you do not need to use.",
                "base_text": "When retired carpenter Tomas Novak first suggested placing two honeybee hives on the flat roof of his apartment building in Prague, several neighbours were sceptical. They assumed that busy streets and exhaust fumes would make the centre of a capital city unsuitable for insects. [gap1] In fact, urban colonies often produce more honey than rural ones because city parks, balcony boxes, and botanical gardens bloom with diverse flowers from early spring until late autumn.\n\nBefore installing the wooden boxes, Tomas spent four months attending a weekend course organised by the local beekeepers' association. [gap2] Once the hives arrived in April, he invited curious residents upstairs in small groups to watch how calmly the worker bees flew in and out toward the chestnut trees along the river. [gap3]\n\nMaintaining rooftop hives still requires careful planning, particularly during hot July afternoons when the dark roof surface warms up quickly. Tomas installed a shaded water tray filled with pebbles so the bees could drink safely without drowning. [gap4] Every September, he gives each household in the building a small jar as a thank-you for their support.\n\nToday, the rooftop project has inspired three nearby schools to plant pollinator-friendly herbs in their courtyards. [gap5]",
                "gaps": ["gap1", "gap2", "gap3", "gap4", "gap5"],
                "options": [
                    {"id": "A", "text": "Seeing the insects up close quickly reassured even the most nervous families on the top floor."},
                    {"id": "B", "text": "However, biologists have found that urban environments can actually be surprisingly healthy for pollinators."},
                    {"id": "C", "text": "Commercial honey imports have risen steadily over the past decade due to supermarket demand."},
                    {"id": "D", "text": "More importantly, it has changed how people on the street notice the seasonal life of their neighbourhood."},
                    {"id": "E", "text": "There, he learned how to inspect frames safely and recognise signs of a healthy queen."},
                    {"id": "F", "text": "Despite these efforts, the council refused permission to build a greenhouse on the pavement."},
                    {"id": "G", "text": "That extra care paid off at the end of the summer when the two colonies yielded thirty kilograms of amber honey."},
                    {"id": "H", "text": "Beeswax candles were once the primary source of indoor lighting across medieval Europe."},
                ],
                "correct": {
                    "gap1": "B",
                    "gap2": "E",
                    "gap3": "A",
                    "gap4": "G",
                    "gap5": "D",
                },
            },
        },

        # ---------------- RT-07: Gapped Text — Paragraphs (5 gaps, 6 options) ----------------
        {
            "skill": "reading",
            "task_type": "RT-07",
            "cefr_target": "C1",
            "difficulty_theta": 1.30,
            "primary_topic": "history_science",
            "scenario": "maritime cartography and acoustic mapping",
            "cognitive_focus": ["discourse_structure", "mental_model_construction", "cohesion"],
            "explanation": "gap1 -> C (lead-line measurements); gap2 -> A (echo sounding revolution in the 1920s); gap3 -> E (Marie Tharp's mid-ocean ridge discovery); gap4 -> B (modern multibeam sonar & satellite altimetry); gap5 -> F (ecological importance of mapping remaining seabed).",
            "content_json": {
                "type": "gapped_text_paragraphs",
                "title": "Charting the Unseen Ocean Floor",
                "instructions": "Five paragraphs have been removed from the feature article below. Choose from paragraphs (A–F) the one which fits each gap (gap1–gap5). There is one extra paragraph you do not need to use.",
                "base_text": "For centuries, mariners crossing the open ocean knew more about the craters of the Moon than the topography lying three kilometres beneath their hulls. While coastal shallows were painstakingly sounded to prevent shipwrecks near harbour approaches, the abyssal plains beyond the continental shelf were widely assumed to be a featureless, stagnant expanse of mud.\n\n[gap1]\n\nThat tedious mechanical method meant that by the early twentieth century, fewer than a few thousand deep-sea soundings existed worldwide—hardly enough to detect vast submarine mountain ranges. A transformative shift occurred only when physicists adapted underwater acoustics to measure depth by timing how long a sound pulse took to rebound from the seabed.\n\n[gap2]\n\nYet raw depth numbers alone could not reveal the tectonic architecture of the planet. In the 1950s, geologist and oceanographic cartographer Marie Tharp painstakingly translatedtens of thousands of sonar profiles into physiographic panoramas of the Atlantic floor.\n\n[gap3]\n\nIn recent decades, single-beam echo sounders have given way to hull-mounted multibeam arrays that fan out dozens of acoustic pulses simultaneously, painting high-resolution swaths across trenches and volcanic seamounts.\n\n[gap4]\n\nCompleting a comprehensive, high-resolution chart of the global seabed is far more than an academic exercise in curiosity.\n\n[gap5]",
                "gaps": ["gap1", "gap2", "gap3", "gap4", "gap5"],
                "options": [
                    {
                        "id": "A",
                        "text": "Instead of halting a vessel for hours, continuous acoustic echo sounders allowed research ships to record uninterrupted depth profiles while steaming at full cruising speed across entire ocean basins.",
                    },
                    {
                        "id": "B",
                        "text": "Complemented by satellite radar altimetry—which infers massive underwater peaks from subtle gravitational bulges on the sea surface—these sonar systems have still mapped only about a quarter of the Earth's oceans at fine resolution.",
                    },
                    {
                        "id": "C",
                        "text": "Gathering even a single deep measurement during the nineteenth century required lowering miles of hemp rope or piano wire weighted with iron sinkers, waiting hours for the line to slacken on impact.",
                    },
                    {
                        "id": "D",
                        "text": "Submarine telegraph cables laid by commercial consortia frequently snapped during winter storms in the North Sea, prompting insurance underwriters to demand higher freight tariffs.",
                    },
                    {
                        "id": "E",
                        "text": "Her hand-drawn maps exposed a continuous 65,000-kilometre mid-ocean ridge bisected by a central rift valley, providing decisive visual proof for the then-controversial theory of continental drift.",
                    },
                    {
                        "id": "F",
                        "text": "Submarine canyons and abyssal ridges steer deep thermohaline currents that regulate global climate, meaning that accurate bathymetry is indispensable for forecasting ocean heat transport and protecting fragile deep-water coral habitats.",
                    },
                ],
                "correct": {
                    "gap1": "C",
                    "gap2": "A",
                    "gap3": "E",
                    "gap4": "B",
                    "gap5": "F",
                },
            },
        },

        # ---------------- RT-08: Comprehension — 5 Items ----------------
        {
            "skill": "reading",
            "task_type": "RT-08",
            "cefr_target": "B1",
            "difficulty_theta": 0.15,
            "primary_topic": "community_culture",
            "scenario": "floating library boat",
            "cognitive_focus": ["gist", "specific_information", "inference", "opinion", "purpose"],
            "explanation": "Q1: B (to bring books to isolated riverside villages); Q2: C (solar panels power the lights and computer); Q3: A (children's storytelling on the upper deck); Q4: B (residents request specific titles in advance); Q5: C (it acts as a social meeting point).",
            "content_json": {
                "type": "multi_mcq",
                "title": "The River Library Boat",
                "passage": "Every second Tuesday, a painted steel barge named The Heron ties up beside the wooden jetty in the village of Millbrook. Inside its converted cargo hold, oak shelves carry nearly four thousand novels, cookbooks, children's picture books, and audiobooks. For twelve small settlements along the winding River Ouse, where the nearest municipal library is forty minutes away by car, The Heron provides a vital service.\n\nThe project began six years ago when retired ferry captain Nora Jenkins noticed how many elderly villagers and young families struggled to reach town after the regional bus route was reduced. With a grant from a regional arts trust, she bought a former grain barge and worked with local apprentices to refit the interior. Solar panels mounted on the wheelhouse roof now generate enough electricity to run the LED reading lamps and the librarian's laptop catalogue.\n\nDuring the summer months, the flat upper deck is covered with a canvas awning and used for Saturday morning storytelling sessions for primary school children. Readers can also reserve specialist gardening or history books online; Nora collects those requests from the central county depot on Monday mornings before setting off upstream.\n\nAs Nora explains, the boat is about more than borrowing paperbacks. 'Half of our regulars stay for twenty minutes just to chat with neighbours they haven't seen all week,' she says. 'When the gangplank goes down, the riverbank turns into a village square.'",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Why did Nora Jenkins originally start the river library project?",
                        "options": [
                            {"id": "A", "text": "The central town library had run out of shelf space for old books."},
                            {"id": "B", "text": "Reduced public transport made it difficult for villagers to visit town."},
                            {"id": "C", "text": "She wanted to teach boat-building skills to university students."},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Paragraph 2 states she noticed villagers struggled to reach town after the regional bus route was reduced.",
                    },
                    {
                        "id": "q2",
                        "stem": "How does The Heron power its lighting and computer system?",
                        "options": [
                            {"id": "A", "text": "By plugging into electricity cables at each village jetty"},
                            {"id": "B", "text": "By running the barge's main diesel engine all day"},
                            {"id": "C", "text": "By using solar panels fitted to the roof of the wheelhouse"},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Paragraph 2 mentions solar panels mounted on the wheelhouse roof generate electricity for the lamps and laptop.",
                    },
                    {
                        "id": "q3",
                        "stem": "What happens on the upper deck of the barge during the summer?",
                        "options": [
                            {"id": "A", "text": "Storytelling events are held for young children."},
                            {"id": "B", "text": "Local authors sell second-hand gardening books."},
                            {"id": "C", "text": "Apprentices repair wooden furniture for villagers."},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Paragraph 3 states the upper deck is used for Saturday morning storytelling sessions for primary school children.",
                    },
                    {
                        "id": "q4",
                        "stem": "What can borrowers do if they want a specific book that is not normally on the boat?",
                        "options": [
                            {"id": "A", "text": "Have it posted directly to their home address"},
                            {"id": "B", "text": "Order it online so Nora can pick it up from the county depot"},
                            {"id": "C", "text": "Ask the village school to print a digital copy"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Paragraph 3 notes readers can reserve books online and Nora collects them from the central county depot.",
                    },
                    {
                        "id": "q5",
                        "stem": "In the final paragraph, what does Nora emphasize about the library boat?",
                        "options": [
                            {"id": "A", "text": "It needs more volunteers to keep the gangplank safe."},
                            {"id": "B", "text": "Audiobooks are becoming more popular than printed novels."},
                            {"id": "C", "text": "It serves as an important social gathering place for the community."},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Nora highlights that regulars stay to chat with neighbours and the riverbank turns into a village square.",
                    },
                ],
            },
        },

        # ---------------- RT-09: Comprehension — 2 Items (B2-C1) ----------------
        {
            "skill": "reading",
            "task_type": "RT-09",
            "cefr_target": "B2",
            "difficulty_theta": 0.65,
            "primary_topic": "psychology_work",
            "scenario": "attention residue in multitasking",
            "cognitive_focus": ["inference", "main_idea"],
            "explanation": "Q1: B (switching tasks leaves part of cognitive focus stuck on the unfinished task); Q2: D (batching messages into scheduled intervals rather than reacting immediately).",
            "content_json": {
                "type": "multi_mcq",
                "title": "The Hidden Cost of Quick Check-Ins",
                "passage": "When knowledge workers glance at an incoming instant message for 'just thirty seconds' before returning to a complex financial report, they rarely count that brief interruption as a significant loss of time. However, organisational psychologist Sophie Leroy coined the term 'attention residue' to describe why such micro-switches are far more taxing than the clock suggests. Even after our eyes return to the primary document, part of our working memory continues processing the unfinished question raised in the message.\n\nThis cognitive carryover is especially pronounced when the interrupted task was open-ended or lacked a clear stopping point. Rather than attempting to maintain perpetual responsiveness throughout the day, researchers found that employees who grouped correspondence into two or three dedicated thirty-minute windows produced analytical work with markedly fewer logical omissions.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "What does the concept of 'attention residue' explain in the first paragraph?",
                        "options": [
                            {"id": "A", "text": "Why employees forget the contents of short instant messages"},
                            {"id": "B", "text": "Why mental focus remains divided even after returning to a main task"},
                            {"id": "C", "text": "Why financial reports take longer to read than emails"},
                            {"id": "D", "text": "Why people prefer open-ended creative projects over routine admin"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "The passage explains that part of working memory continues processing the prior task even after returning to the primary document.",
                    },
                    {
                        "id": "q2",
                        "stem": "According to the second paragraph, how can workers reduce cognitive carryover most effectively?",
                        "options": [
                            {"id": "A", "text": "By replying to every message in under thirty seconds"},
                            {"id": "B", "text": "By delegating all analytical proofreading to colleagues"},
                            {"id": "C", "text": "By avoiding tasks that require complex logical reasoning"},
                            {"id": "D", "text": "By handling messages during set time blocks rather than continuously"},
                        ],
                        "correct_option_id": "D",
                        "explanation": "Researchers found that grouping correspondence into dedicated thirty-minute windows reduced logical omissions.",
                    },
                ],
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-09",
            "cefr_target": "C1",
            "difficulty_theta": 1.55,
            "primary_topic": "economics_arts",
            "scenario": "museum conservation ethics",
            "cognitive_focus": ["attitude", "inference"],
            "explanation": "Q1: C (modern restorers make repairs subtly distinguishable and reversible rather than disguising them permanently); Q2: A (varnish removal can strip away deliberate tonal glazes applied by the original painter).",
            "content_json": {
                "type": "multi_mcq",
                "title": "The Ethics of Invisible Restoration",
                "passage": "Nineteenth-century picture restorers often viewed themselves as co-authors with the Old Masters, cheerfully repainting damaged drapery and slathering amber-tinted varnishes across canvases to manufacture an artificial glow of antiquity. Contemporary conservation ethics, by contrast, rest on the twin pillars of reversibility and legibility. Any pigment introduced to bridge a tear in a seventeenth-century portrait must be formulated with synthetic resins that a future conservator could dissolve without disturbing a single original brushstroke beneath.\n\nEven so, fierce controversies periodically erupt when galleries unveil newly cleaned masterpieces. Critics argue that aggressive solvent cleaning—intended to strip away centuries of candle soot—can inadvertently remove delicate final glazes that the artist deliberately applied to soften harsh contrasts, leaving figures looking jarring and clinically bright to modern eyes.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "How does modern conservation practice differ from nineteenth-century restoration?",
                        "options": [
                            {"id": "A", "text": "Modern conservators refuse to repair tears in seventeenth-century portraits."},
                            {"id": "B", "text": "Modern conservators prefer natural amber varnishes over synthetic resins."},
                            {"id": "C", "text": "Modern interventions are designed so they can later be safely undone."},
                            {"id": "D", "text": "Modern galleries encourage restorers to update the style of damaged areas."},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Contemporary ethics emphasize reversibility: using synthetic resins that future conservators can dissolve safely.",
                    },
                    {
                        "id": "q2",
                        "stem": "Why do some critics object to intensive solvent cleaning of old paintings?",
                        "options": [
                            {"id": "A", "text": "It may erase subtle surface layers that the painter originally intended."},
                            {"id": "B", "text": "It causes candle soot to sink deeper into the canvas fibres."},
                            {"id": "C", "text": "It makes synthetic resins impossible to remove in the future."},
                            {"id": "D", "text": "It darkens the colours until figures can no longer be seen clearly."},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Critics argue solvent cleaning can remove delicate final glazes the artist deliberately applied.",
                    },
                ],
            },
        },
    ]


def get_initial_listening_items() -> List[Dict[str, Any]]:
    """
    Original Listening question bank covering LT-01 (1-item), LT-02 (2-item), and LT-03 (5-item)
    across CEFR A1-C1 and monologue/dialogue/discussion scenarios (PRD Section 11).
    """
    return [
        # ---------------- LT-01: 1-Item Comprehension ----------------
        {
            "skill": "listening",
            "task_type": "LT-01",
            "cefr_target": "A1",
            "difficulty_theta": -1.45,
            "primary_topic": "appointments",
            "scenario": "dental appointment voicemail",
            "cognitive_focus": ["specific_information"],
            "explanation": "The receptionist says the new appointment time is at 10:30 on Wednesday morning.",
            "content_json": {
                "type": "mcq",
                "title": "Voicemail from Green Park Dental Clinic",
                "prelistening_seconds": 8,
                "speaker_meta": {
                    "speaker_count": 1,
                    "speaker_roles": ["receptionist"],
                    "accent_profile": "international_English",
                    "speech_speed": "A1",
                    "register": "polite_neutral",
                },
                "transcript": "Hello, this is Green Park Dental Clinic calling for Samira. Dr. Evans is unwell today, so we need to move your Tuesday afternoon check-up. Your new appointment is on Wednesday morning at ten thirty. Please call us back if you cannot make it.",
                "stem": "When is Samira's new dental appointment?",
                "options": [
                    {"id": "A", "text": "Tuesday afternoon at 2:30"},
                    {"id": "B", "text": "Wednesday morning at 10:30"},
                    {"id": "C", "text": "Thursday morning at 10:00"},
                ],
                "correct_option_id": "B",
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-01",
            "cefr_target": "A2",
            "difficulty_theta": -0.70,
            "primary_topic": "shopping_services",
            "scenario": "returning a jacket in a clothes shop",
            "cognitive_focus": ["detail", "reason"],
            "explanation": "The customer says the sleeves are too short when he stretches his arms, even though he likes the dark green colour.",
            "content_json": {
                "type": "mcq",
                "title": "At a Clothing Store Desk",
                "prelistening_seconds": 10,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["shop_assistant", "customer"],
                    "accent_profile": "international_English",
                    "speech_speed": "A2",
                    "register": "everyday_polite",
                },
                "transcript": "Assistant: Good morning! How can I help you with that rain jacket?\nCustomer: Hi, I bought this medium jacket yesterday. I really love the dark green colour, and the zip works fine, but when I rode my bike this morning I realised the sleeves are much too short for my arms. Do you have the large size in stock?",
                "stem": "Why does the man want to exchange the rain jacket?",
                "options": [
                    {"id": "A", "text": "The front zip is broken"},
                    {"id": "B", "text": "He prefers a different colour"},
                    {"id": "C", "text": "The sleeves are not long enough"},
                ],
                "correct_option_id": "C",
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-01",
            "cefr_target": "B1",
            "difficulty_theta": 0.05,
            "primary_topic": "travel",
            "scenario": "station platform announcement",
            "cognitive_focus": ["specific_information", "inference"],
            "explanation": "Passengers for the airport should stay in the front four carriages because the rear two carriages will detach at Central Junction.",
            "content_json": {
                "type": "mcq",
                "title": "Train Announcement to North Airport",
                "prelistening_seconds": 10,
                "speaker_meta": {
                    "speaker_count": 1,
                    "speaker_roles": ["station_announcer"],
                    "accent_profile": "international_English",
                    "speech_speed": "B1",
                    "register": "public_announcement",
                },
                "transcript": "Attention please. The sixteen twenty service to North Airport and Harbour Bay will depart from Platform Three in five minutes. Please note that this six-carriage train will divide at Central Junction. Passengers travelling to North Airport must travel in the front four carriages, as the rear two carriages will continue only to Harbour Bay.",
                "stem": "What must passengers travelling to North Airport do?",
                "options": [
                    {"id": "A", "text": "Sit in the first four carriages of the train"},
                    {"id": "B", "text": "Change to a bus at Central Junction"},
                    {"id": "C", "text": "Board from Platform Six instead of Platform Three"},
                ],
                "correct_option_id": "A",
            },
        },

        # ---------------- LT-02: 2-Item Comprehension ----------------
        {
            "skill": "listening",
            "task_type": "LT-02",
            "cefr_target": "B2",
            "difficulty_theta": 0.75,
            "primary_topic": "workplace",
            "scenario": "colleagues reviewing a client workshop",
            "cognitive_focus": ["attitude", "inference", "agreement"],
            "explanation": "Q1: B (Elena felt the afternoon breakout exercises ran out of time); Q2: C (Both agree to send the case-study briefing two days before the next event).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Debriefing After a Training Day",
                "prelistening_seconds": 12,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["project_lead", "facilitator"],
                    "accent_profile": "international_English",
                    "speech_speed": "B2",
                    "register": "professional_colloquial",
                },
                "transcript": "David: Well, Elena, the feedback forms from yesterday's software onboarding workshop look encouraging overall. Most participants praised the live demonstration.\nElena: True, the morning demo went smoothly, David, though I couldn't help feeling we squeezed the afternoon troubleshooting exercises into far too tight a window. Just as the groups were getting into the sample data, we had to wrap up.\nDavid: Fair point. We spent twenty minutes just explaining the background scenario. What if, for next month's cohort, we email the background case study forty-eight hours in advance?\nElena: That would solve it. Then we can jump straight into hands-on problem solving right after lunch.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "What criticism does Elena make about yesterday's workshop?",
                        "options": [
                            {"id": "A", "text": "The morning software demonstration was too technical."},
                            {"id": "B", "text": "There was not enough time for the afternoon group activities."},
                            {"id": "C", "text": "Participants failed to complete the feedback forms."},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Elena states they squeezed the afternoon troubleshooting exercises into far too tight a window.",
                    },
                    {
                        "id": "q2",
                        "stem": "What do David and Elena agree to change for next month's session?",
                        "options": [
                            {"id": "A", "text": "Cancel the live demonstration in the morning"},
                            {"id": "B", "text": "Extend the workshop into a two-day course"},
                            {"id": "C", "text": "Share the reading material with participants before the day"},
                        ],
                        "correct_option_id": "C",
                        "explanation": "David proposes emailing the background case study 48 hours in advance and Elena agrees.",
                    },
                ],
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-02",
            "cefr_target": "C1",
            "difficulty_theta": 1.40,
            "primary_topic": "media_culture",
            "scenario": "documentary filmmaker interview",
            "cognitive_focus": ["implied_meaning", "attitude"],
            "explanation": "Q1: A (He avoided voice-over narration so viewers interpret the artisans' gestures directly); Q2: B (Winning over the workshop apprentices' trust took months of unfilmed visits).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Interview with a Documentary Director",
                "prelistening_seconds": 12,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["radio_host", "director"],
                    "accent_profile": "international_English",
                    "speech_speed": "C1",
                    "register": "broadcast_discussion",
                },
                "transcript": "Host: Your new documentary on traditional violin makers in Cremona contains almost no spoken commentary at all. Was that a stylistic gamble, Marco?\nDirector: Viewers are so accustomed to a booming narrator telling them what to feel at every cut. Once we stripped away the explanatory script, the rhythmic scraping of planes against maple wood and the quiet glances between master and apprentice carried far more narrative weight than any historian's summary could.\nHost: And how did the luthiers react to having cameras in such cramped quarters?\nDirector: Honestly, if we had turned up with tripods on day one, they would have given us polite, rehearsed answers. I spent the first six weeks simply sweeping wood shavings and drinking espresso with them without a lens in sight until my presence became completely unremarkable.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Why did Marco decide against using a narrator in his documentary?",
                        "options": [
                            {"id": "A", "text": "He believed the workshop sounds and visual details spoke for themselves."},
                            {"id": "B", "text": "He could not find a historian who understood violin acoustics."},
                            {"id": "C", "text": "The workshop was too noisy to record clear spoken commentary."},
                        ],
                        "correct_option_id": "A",
                        "explanation": "He explains that the workshop sounds and quiet glances carried more narrative weight without an explanatory script.",
                    },
                    {
                        "id": "q2",
                        "stem": "How did Marco ensure the violin makers behaved naturally during filming?",
                        "options": [
                            {"id": "A", "text": "By using hidden cameras mounted in the ceiling"},
                            {"id": "B", "text": "By spending weeks visiting them casually before bringing equipment"},
                            {"id": "C", "text": "By paying the apprentices to interview one another"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "He spent the first six weeks visiting without a lens in sight until his presence became unremarkable.",
                    },
                ],
            },
        },

        # ---------------- LT-03: 5-Item Comprehension (3 speakers / extended monologue) ----------------
        {
            "skill": "listening",
            "task_type": "LT-03",
            "cefr_target": "B1",
            "difficulty_theta": 0.15,
            "primary_topic": "community_events",
            "scenario": "organising a neighbourhood botanical festival",
            "cognitive_focus": ["detail", "inference", "attitude", "global_meaning"],
            "explanation": "Q1: B (moved to the covered market hall because of rain forecast); Q2: A (Hannah's brother is lending the sound system); Q3: C (seed-swap table needs paper envelopes); Q4: B (local bakery is providing savoury pastries); Q5: A (put up directional signs from the tram stop).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Planning the Spring Plant Exchange",
                "prelistening_seconds": 15,
                "speaker_meta": {
                    "speaker_count": 3,
                    "speaker_roles": ["organiser_omar", "volunteer_hannah", "treasurer_liam"],
                    "accent_profile": "international_English",
                    "speech_speed": "B1",
                    "register": "collaborative_informal",
                },
                "transcript": "Omar: Thanks for meeting up, Hannah and Liam. With the Spring Plant Exchange happening this Sunday, we need to finalise our wet-weather plan. The forecast predicts heavy showers all afternoon, so I've spoken to the council and shifted our stalls from the open lawn into the Old Covered Market Hall.\nHannah: Oh, that's a relief! At least the seedlings won't get washed away. Does the market hall have a microphone for the gardening talks, Omar?\nOmar: Unfortunately not. Their PA system is being repaired.\nHannah: No problem—my brother plays in an acoustic band and he's already offered to lend us his portable speaker and wireless microphone for the day.\nLiam: Brilliant, that saves us hiring equipment from the budget. Speaking of supplies, I checked the seed-swap crates this morning. We have plenty of tomato, basil, and sunflower seeds donated by local allotment holders, but we've almost run out of small paper envelopes to pack them in.\nHannah: I can pick up five hundred brown paper packets from the stationery shop tomorrow morning.\nOmar: Thanks, Hannah. Now, what about refreshments? Liam, did the riverside café confirm?\nLiam: They couldn't spare staff on a Sunday, so I arranged for Miller's Bakery on High Street to deliver four trays of cheese and spinach pastries along with apple juice at eleven o'clock.\nOmar: Great. Since we changed the venue from the park lawn to the Covered Market Hall, our last job on Sunday morning at eight thirty is to tie bright yellow arrow signs from the Eastgate tram stop so visitors don't walk to the wrong entrance.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Why has the venue for the Spring Plant Exchange been changed?",
                        "options": [
                            {"id": "A", "text": "The park lawn is being reseeded by the council."},
                            {"id": "B", "text": "Heavy rain is forecast for Sunday afternoon."},
                            {"id": "C", "text": "More stallholders registered than expected."},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Omar says the forecast predicts heavy showers all afternoon, so he shifted the stalls into the Old Covered Market Hall.",
                    },
                    {
                        "id": "q2",
                        "stem": "How will the team get audio equipment for the gardening talks?",
                        "options": [
                            {"id": "A", "text": "Hannah's brother will lend them his portable system."},
                            {"id": "B", "text": "Liam will rent a microphone using club funds."},
                            {"id": "C", "text": "The market hall caretaker will repair the built-in speakers."},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Hannah says her brother offered to lend his portable speaker and wireless microphone.",
                    },
                    {
                        "id": "q3",
                        "stem": "What item does Hannah agree to buy before Sunday?",
                        "options": [
                            {"id": "A", "text": "Extra packets of sunflower seeds"},
                            {"id": "B", "text": "Plastic trays for carrying seedlings"},
                            {"id": "C", "text": "Small paper envelopes for the seed swap"},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Liam notes they ran out of small paper envelopes, and Hannah offers to buy 500 packets.",
                    },
                    {
                        "id": "q4",
                        "stem": "Who will provide the food and drinks for the event?",
                        "options": [
                            {"id": "A", "text": "The riverside café"},
                            {"id": "B", "text": "Miller's Bakery on High Street"},
                            {"id": "C", "text": "Volunteers from the allotment society"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Liam arranged for Miller's Bakery to deliver savoury pastries and apple juice.",
                    },
                    {
                        "id": "q5",
                        "stem": "What will the organisers do at 8:30 on Sunday morning?",
                        "options": [
                            {"id": "A", "text": "Put up direction signs from the tram stop to the new venue"},
                            {"id": "B", "text": "Collect tables from the council storage depot"},
                            {"id": "C", "text": "Print programmes at the stationery shop"},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Omar says their job at 8:30 is to tie yellow arrow signs from the Eastgate tram stop.",
                    },
                ],
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-03",
            "cefr_target": "B2",
            "difficulty_theta": 0.85,
            "primary_topic": "education_science",
            "scenario": "university podcast on campus dark-sky observatory",
            "cognitive_focus": ["gist", "detail", "inference", "attitude", "global_meaning"],
            "explanation": "Q1: C (LED streetlamp shielding reduced skyglow); Q2: B (biology students track nocturnal moth navigation); Q3: A (Thursday public evenings book out quickly); Q4: D (weather sensors automatically close the dome); Q5: C (she feels proud that non-science majors use the facility).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Campus Observatory Restores Night Sky",
                "prelistening_seconds": 15,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["interviewer", "dr_chen_astrophysicist"],
                    "accent_profile": "international_English",
                    "speech_speed": "B2",
                    "register": "academic_accessible",
                },
                "transcript": "Interviewer: Five years ago, the astronomy dome on North Hill Campus was nearly decommissioned because urban light pollution washed out faint stars. Yet today, Dr. Nadia Chen, your team is recording clearer images than ever. What changed?\nDr. Chen: People assume we installed a giant new mirror, but the breakthrough was actually on the ground. We collaborated with the university estates department and the town council to fit downward-facing shields and warm-spectrum filters onto two thousand campus and street lamps. By stopping light from spilling upward into the atmosphere, background skyglow dropped by nearly half.\nInterviewer: And it wasn't just physicists who benefited from darker campus pathways, was it?\nDr. Chen: Not at all! The ecology department immediately launched a joint study with us. Their postgraduate students found that nocturnal pollinators—especially hawkmoths—recovered their natural feeding behaviour once the harsh blue glare around the botanical beds was toned down.\nInterviewer: You also opened the dome to local residents this semester.\nDr. Chen: Yes, every Thursday evening we host twenty visitors. Because the dome walkway is narrow, people do have to reserve a free pass online on Monday mornings, and they usually go within an hour.\nInterviewer: Do undergraduate students operate the telescope overnight?\nDr. Chen: They can actually schedule observations remotely from their dorms! We wired the roof shutters to an ultrasonic rain and humidity sensor, so if clouds roll in at three in the morning, the dome seals itself automatically before a single drop hits the optics. Honestly, what delights me most is seeing fine-arts and literature undergraduates booking viewing slots alongside physics majors.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "What was the main reason the observatory's viewing conditions improved?",
                        "options": [
                            {"id": "A", "text": "The dome was relocated to a higher hill outside town."},
                            {"id": "B", "text": "A larger telescope mirror was imported from abroad."},
                            {"id": "C", "text": "Outdoor lighting was modified to point downward with warmer filters."},
                            {"id": "D", "text": "All streetlamps near the campus were switched off after midnight."},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Dr. Chen explains they fitted downward-facing shields and warm-spectrum filters onto 2,000 lamps.",
                    },
                    {
                        "id": "q2",
                        "stem": "How did the ecology department make use of the lighting changes?",
                        "options": [
                            {"id": "A", "text": "By growing rare alpine plants inside the observatory grounds"},
                            {"id": "B", "text": "By studying how night-flying insects responded to reduced glare"},
                            {"id": "C", "text": "By testing solar-powered batteries on campus pathways"},
                            {"id": "D", "text": "By tracking bird migration using the telescope cameras"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Postgraduates studied how nocturnal pollinators like hawkmoths recovered natural feeding behaviour.",
                    },
                    {
                        "id": "q3",
                        "stem": "What does Dr. Chen mention about the Thursday evening public sessions?",
                        "options": [
                            {"id": "A", "text": "Visitors must book a free ticket online in advance because space is limited."},
                            {"id": "B", "text": "They are only open to school groups of more than thirty students."},
                            {"id": "C", "text": "Tickets cost ten pounds to help pay for telescope maintenance."},
                            {"id": "D", "text": "They take place only during the winter examination break."},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Because the walkway is narrow, 20 visitors must reserve a free pass online on Monday mornings.",
                    },
                    {
                        "id": "q4",
                        "stem": "How is the telescope protected during remote overnight observations?",
                        "options": [
                            {"id": "A", "text": "A night watchman stays inside the control room until dawn."},
                            {"id": "B", "text": "Students must remain in the dome whenever the shutter is open."},
                            {"id": "C", "text": "A glass cover remains permanently fixed over the lens."},
                            {"id": "D", "text": "Weather sensors automatically shut the roof if rain or humidity rises."},
                        ],
                        "correct_option_id": "D",
                        "explanation": "Roof shutters are wired to an ultrasonic rain and humidity sensor that seals the dome automatically.",
                    },
                    {
                        "id": "q5",
                        "stem": "What pleases Dr. Chen most about the observatory's current use?",
                        "options": [
                            {"id": "A", "text": "It has reduced the university's annual heating bill."},
                            {"id": "B", "text": "It has won an international architectural prize."},
                            {"id": "C", "text": "Students from arts and humanities subjects also use it."},
                            {"id": "D", "text": "It no longer requires any maintenance from staff."},
                        ],
                        "correct_option_id": "C",
                        "explanation": "She says what delights her most is seeing fine-arts and literature undergraduates booking slots alongside physics majors.",
                    },
                ],
            },
        },
    ]


def get_initial_writing_prompts() -> List[Dict[str, Any]]:
    """
    Original Writing Prompts for Part 1 (Email, min 50 words, ~15 min)
    and Part 2 (Wider-audience writing: article, review, web post, min 180 words, ~30 min)
    per PRD Section 12.
    """
    return [
        # ---------------- PART 1: EMAIL (min 50 words, ~15 min) ----------------
        {
            "task_part": 1,
            "cefr_target": "B1",
            "text_type": "email",
            "audience": "an English-speaking friend (Alex)",
            "scenario": "Your friend Alex helped you organise a weekend photography exhibition at your local community centre last Saturday.",
            "prompt_text": "Read this message from your friend Alex:\n\n\"Hi! I really enjoyed helping out at your photography exhibition on Saturday morning, though I had to leave early before it finished. How did the rest of the afternoon go? Let me know when we can meet up this week so I can return the camera tripod I borrowed from you!\"\n\nWrite an email to Alex. Write at least 50 words.",
            "bullet_points": [
                "thank Alex for helping at the exhibition",
                "describe how the rest of the afternoon went",
                "suggest a day and place to meet this week to get your tripod back",
            ],
            "minimum_words": 50,
            "recommended_minutes": 15,
            "status": "APPROVED",
        },
        {
            "task_part": 1,
            "cefr_target": "B2",
            "text_type": "email",
            "audience": "Course Coordinator (Ms. Clara Bennett)",
            "scenario": "You are enrolled in an evening professional communication course at a local college, and you need to miss next Tuesday's class due to a work trip.",
            "prompt_text": "You have received an email from your evening course coordinator, Ms. Clara Bennett, reminding students that project topics and group partners will be assigned during next Tuesday's session.\n\nWrite an email to Ms. Bennett. Write at least 50 words.",
            "bullet_points": [
                "explain why you cannot attend next Tuesday's evening session",
                "state which project topic you would prefer to work on and why",
                "ask how you can access the slides or handouts from the missed class",
            ],
            "minimum_words": 50,
            "recommended_minutes": 15,
            "status": "APPROVED",
        },
        {
            "task_part": 1,
            "cefr_target": "A2",
            "text_type": "email",
            "audience": "a neighbour (Sam)",
            "scenario": "You are going away for three days next weekend and want to ask your neighbour Sam for a small favour.",
            "prompt_text": "You are travelling to visit relatives from Friday morning to Sunday evening. Write an email to your neighbour, Sam. Write at least 50 words.",
            "bullet_points": [
                "tell Sam where you are going next weekend",
                "ask Sam to water your balcony plants and collect a parcel on Saturday",
                "explain where you will leave your apartment key",
            ],
            "minimum_words": 50,
            "recommended_minutes": 15,
            "status": "APPROVED",
        },

        # ---------------- PART 2: WIDER-AUDIENCE WRITING (min 180 words, ~30 min) ----------------
        {
            "task_part": 2,
            "cefr_target": "B2",
            "text_type": "article",
            "audience": "readers of an international online lifestyle and study magazine",
            "scenario": "An online magazine is inviting readers to submit articles about learning practical skills outside formal classrooms.",
            "prompt_text": "You see this announcement on an international English-language website:\n\n\"LEARNING BEYOND THE CLASSROOM\nHave you ever learned a useful practical skill—such as cooking, repairing things, coding, playing an instrument, or gardening—on your own or from someone in your community? Write an article for our readers!\"\n\nWrite an article addressing the points below. Write at least 180 words.",
            "bullet_points": [
                "describe a practical skill you learned outside school or university and how you learned it",
                "explain what challenges you faced while practising this skill",
                "discuss whether self-directed learning is more rewarding than taking a formal course",
            ],
            "minimum_words": 180,
            "recommended_minutes": 30,
            "status": "APPROVED",
        },
        {
            "task_part": 2,
            "cefr_target": "B2",
            "text_type": "review",
            "audience": "visitors to a public culture and technology website",
            "scenario": "A consumer and culture website is asking readers to review a digital app, website, or public facility that has improved their daily routine.",
            "prompt_text": "You read this request on a community review portal:\n\n\"TOOLS & PLACES THAT MAKE DAILY LIFE BETTER\nWrite a review of a public facility (such as a library, sports centre, or park) OR a digital tool that has made a positive difference to your weekly routine.\"\n\nWrite a review addressing the points below. Write at least 180 words.",
            "bullet_points": [
                "introduce the facility or digital tool and explain how often you use it",
                "highlight its strongest features as well as one aspect that could be improved",
                "explain who would benefit most from using it and why",
            ],
            "minimum_words": 180,
            "recommended_minutes": 30,
            "status": "APPROVED",
        },
        {
            "task_part": 2,
            "cefr_target": "C1",
            "text_type": "web_post",
            "audience": "subscribers to a professional workplace discussion forum",
            "scenario": "A professional forum is hosting a debate on whether companies and universities should shorten the standard working/study week to four days.",
            "prompt_text": "You are contributing a detailed discussion post to an international workplace and education forum on the topic of a four-day week.\n\nWrite a forum post addressing the points below. Write at least 180 words.",
            "bullet_points": [
                "evaluate how a four-day schedule could affect productivity and personal well-being",
                "consider the practical difficulties certain industries or institutions might face",
                "propose how organisations can measure output fairly without relying solely on hours spent at a desk",
            ],
            "minimum_words": 180,
            "recommended_minutes": 30,
            "status": "APPROVED",
        },
    ]


def ensure_seed_bank(db: Session) -> Dict[str, int]:
    """
    Idempotently seeds the initial approved question bank (Reading, Listening with generated local WAV audio,
    and Writing prompts) so Practice Mode and Full Test Simulation work immediately out of the box.
    Also creates a couple of items in REVIEW status so the Content Studio Review Queue is demonstrable right away.
    """
    existing_questions = db.query(QuestionItem).count()
    existing_writing = db.query(WritingPrompt).count()

    seeded_reading = 0
    seeded_listening = 0
    seeded_writing = 0

    if existing_questions == 0:
        # 1. Seed base items + multi-level variants so bank health targets across A1-C1 are well populated
        base_reading = get_initial_reading_items()
        base_listening = get_initial_listening_items()

        # Expand reading bank with additional calibrated items across A1-C1 so adaptive sessions never run dry
        extra_reading = _build_supplementary_reading_items()
        extra_listening = _build_supplementary_listening_items()

        all_reading = base_reading + extra_reading
        all_listening = base_listening + extra_listening

        for idx, item_data in enumerate(all_reading):
            c_hash = compute_content_hash(item_data["content_json"])
            v_report = validate_question_item(
                skill="reading",
                task_type=item_data["task_type"],
                cefr_target=item_data["cefr_target"],
                difficulty_theta=item_data["difficulty_theta"],
                content_json=item_data["content_json"],
                explanation=item_data["explanation"],
            )
            q_item = QuestionItem(
                skill="reading",
                task_type=item_data["task_type"],
                cefr_target=item_data["cefr_target"],
                difficulty_theta=item_data["difficulty_theta"],
                status=item_data.get("status", "APPROVED"),
                version=1,
                content_hash=c_hash,
                primary_topic=item_data["primary_topic"],
                scenario=item_data["scenario"],
                cognitive_focus=item_data["cognitive_focus"],
                content_json=item_data["content_json"],
                explanation=item_data["explanation"],
                validation_report=v_report,
            )
            db.add(q_item)
            seeded_reading += 1

        db.flush()

        for item_data in all_listening:
            c_hash = compute_content_hash(item_data["content_json"])
            v_report = validate_question_item(
                skill="listening",
                task_type=item_data["task_type"],
                cefr_target=item_data["cefr_target"],
                difficulty_theta=item_data["difficulty_theta"],
                content_json=item_data["content_json"],
                explanation=item_data["explanation"],
            )
            q_item = QuestionItem(
                skill="listening",
                task_type=item_data["task_type"],
                cefr_target=item_data["cefr_target"],
                difficulty_theta=item_data["difficulty_theta"],
                status=item_data.get("status", "APPROVED"),
                version=1,
                content_hash=c_hash,
                primary_topic=item_data["primary_topic"],
                scenario=item_data["scenario"],
                cognitive_focus=item_data["cognitive_focus"],
                content_json=item_data["content_json"],
                explanation=item_data["explanation"],
                validation_report=v_report,
            )
            db.add(q_item)
            db.flush()

            # Generate local WAV audio asset for each listening item
            transcript = item_data["content_json"].get("transcript", "")
            spk_meta = item_data["content_json"].get("speaker_meta", {})
            audio_info = tts_engine.generate_audio_asset(
                question_id=q_item.id,
                script_text=transcript,
                speaker_count=spk_meta.get("speaker_count", 1),
                voice="en_voice_01",
            )
            asset = AudioAsset(
                question_id=q_item.id,
                file_path=audio_info["file_path"],
                duration_seconds=audio_info["duration_seconds"],
                format=audio_info["format"],
                voice=audio_info["voice"],
                tts_provider=audio_info["tts_provider"],
                script_hash=audio_info["script_hash"],
                status=audio_info["status"],
            )
            db.add(asset)
            seeded_listening += 1

    if existing_writing == 0:
        for wp in get_initial_writing_prompts():
            prompt_obj = WritingPrompt(
                task_part=wp["task_part"],
                cefr_target=wp["cefr_target"],
                text_type=wp["text_type"],
                audience=wp["audience"],
                scenario=wp["scenario"],
                prompt_text=wp["prompt_text"],
                bullet_points=wp["bullet_points"],
                minimum_words=wp["minimum_words"],
                recommended_minutes=wp["recommended_minutes"],
                status=wp.get("status", "APPROVED"),
                version=1,
                validation_report={"valid": True, "errors": [], "warnings": []},
            )
            db.add(prompt_obj)
            seeded_writing += 1

    db.commit()
    return {
        "seeded_reading": seeded_reading,
        "seeded_listening": seeded_listening,
        "seeded_writing": seeded_writing,
    }


def _build_supplementary_reading_items() -> List[Dict[str, Any]]:
    """Additional original Reading items across A1-C1 to ensure rich adaptive depth and Review Queue items."""
    return [
        {
            "skill": "reading",
            "task_type": "RT-05",
            "cefr_target": "A1",
            "difficulty_theta": -1.65,
            "primary_topic": "transport",
            "scenario": "bicycle park sign",
            "cognitive_focus": ["specific_information"],
            "explanation": "The sign states 'Maximum stay: 24 hours' and 'Free of charge for station passengers'.",
            "content_json": {
                "type": "discrete_graphic",
                "graphic": {
                    "graphic_type": "notice",
                    "header": "STATION BICYCLE RACKS — NORTH ENTRANCE",
                    "subtext": "CCTV Monitored Area",
                    "body": "• Free of charge for train passengers.\n• Maximum stay: 24 hours.\n• Please lock both wheels to the metal frame.",
                    "footer": "Station Management",
                },
                "stem": "How long can passengers leave their bicycles at the North Entrance racks?",
                "options": [
                    {"id": "A", "text": "Up to 24 hours"},
                    {"id": "B", "text": "For an entire week"},
                    {"id": "C", "text": "Only until 6 p.m."},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "A2",
            "difficulty_theta": -0.90,
            "primary_topic": "health_lifestyle",
            "scenario": "sports class",
            "cognitive_focus": ["lexical_access"],
            "explanation": "'beginners' refers to people who are learning an activity for the first time.",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "The Tuesday evening yoga class is suitable for complete ________ who have never tried yoga before.",
                "options": [
                    {"id": "A", "text": "beginners"},
                    {"id": "B", "text": "strangers"},
                    {"id": "C", "text": "visitors"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "B2",
            "difficulty_theta": 0.55,
            "primary_topic": "workplace",
            "scenario": "project deadline",
            "cognitive_focus": ["lexical_access", "grammar"],
            "explanation": "'Provided that' introduces a necessary condition ('on condition that').",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "________ that the supplier delivers the optical sensors by Wednesday, assembly will finish on schedule.",
                "options": [
                    {"id": "A", "text": "Provided"},
                    {"id": "B", "text": "Unless"},
                    {"id": "C", "text": "Whereas"},
                    {"id": "D", "text": "Suppose"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "reading",
            "task_type": "RT-08",
            "cefr_target": "A1",
            "difficulty_theta": -1.30,
            "primary_topic": "daily_life",
            "scenario": "community café menu and opening",
            "cognitive_focus": ["specific_information", "gist"],
            "explanation": "Q1: B (next to the town library); Q2: A (homemade vegetable soup); Q3: C (students get 15% discount); Q4: A (board games on Friday evening); Q5: B (apply at the counter).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Welcome to The Green Leaf Café",
                "passage": "The Green Leaf Café opened last month on Market Street, right next to the town library. We serve fresh coffee, herbal teas, and light lunches from Monday to Saturday between 8:00 a.m. and 6:00 p.m.\n\nOur most popular lunch dish is our warm homemade vegetable soup, served with brown bread from the local bakery. Every afternoon after 2:00 p.m., university and college students receive a 15% discount on all hot drinks when they show their student card.\n\nOn Friday evenings, we keep the café open until 9:00 p.m. for our neighbourhood board-game night. Bring a friend or join a table! We are also looking for a part-time weekend server. If you would like to join our friendly team, please ask Marco for an application form at the counter.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Where is The Green Leaf Café located?",
                        "options": [
                            {"id": "A", "text": "Inside the university sports hall"},
                            {"id": "B", "text": "Next to the town library on Market Street"},
                            {"id": "C", "text": "Opposite the central train station"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Paragraph 1 says it opened on Market Street, right next to the town library.",
                    },
                    {
                        "id": "q2",
                        "stem": "What is the café's most popular lunch item?",
                        "options": [
                            {"id": "A", "text": "Homemade vegetable soup with bread"},
                            {"id": "B", "text": "Grilled chicken sandwiches"},
                            {"id": "C", "text": "Fruit salad and yoghurt"},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Paragraph 2 states their most popular lunch dish is warm homemade vegetable soup with brown bread.",
                    },
                    {
                        "id": "q3",
                        "stem": "How can students get a discount after 2:00 p.m.?",
                        "options": [
                            {"id": "A", "text": "By bringing their own coffee cup"},
                            {"id": "B", "text": "By ordering two lunches together"},
                            {"id": "C", "text": "By showing their student card"},
                        ],
                        "correct_option_id": "C",
                        "explanation": "Students receive a 15% discount when they show their student card.",
                    },
                    {
                        "id": "q4",
                        "stem": "Why does the café stay open until 9:00 p.m. on Fridays?",
                        "options": [
                            {"id": "A", "text": "For a board-game evening"},
                            {"id": "B", "text": "For a live guitar concert"},
                            {"id": "C", "text": "For a cooking class"},
                        ],
                        "correct_option_id": "A",
                        "explanation": "Paragraph 3 mentions Friday evenings stay open until 9:00 p.m. for neighbourhood board-game night.",
                    },
                    {
                        "id": "q5",
                        "stem": "What should someone do if they want the weekend job?",
                        "options": [
                            {"id": "A", "text": "Phone the town library manager"},
                            {"id": "B", "text": "Ask Marco for a form at the café counter"},
                            {"id": "C", "text": "Post a letter to the local bakery"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Applicants are instructed to ask Marco for an application form at the counter.",
                    },
                ],
            },
        },
        # One pre-populated item in REVIEW status so Content Studio Review Queue is immediately interactive
        {
            "skill": "reading",
            "task_type": "RT-04",
            "cefr_target": "B2",
            "difficulty_theta": 0.60,
            "status": "REVIEW",
            "primary_topic": "environment",
            "scenario": "coastal conservation",
            "cognitive_focus": ["lexical_access", "collocation"],
            "explanation": "'instrumental' collocates with 'in' ('was instrumental in securing') meaning played a key role.",
            "content_json": {
                "type": "discrete_cloze",
                "stem": "Local marine biologists were ________ in persuading the harbour authority to protect the seagrass meadows.",
                "options": [
                    {"id": "A", "text": "instrumental"},
                    {"id": "B", "text": "operational"},
                    {"id": "C", "text": "mechanical"},
                    {"id": "D", "text": "beneficial"},
                ],
                "correct_option_id": "A",
            },
        },
    ]


def _build_supplementary_listening_items() -> List[Dict[str, Any]]:
    """Additional original Listening items across A1-C1 so adaptive listening sessions have rich variety."""
    return [
        {
            "skill": "listening",
            "task_type": "LT-01",
            "cefr_target": "A1",
            "difficulty_theta": -1.35,
            "primary_topic": "daily_life",
            "scenario": "weather forecast for saturday",
            "cognitive_focus": ["specific_information"],
            "explanation": "The presenter says Saturday morning will be sunny and dry, while rain arrives only late on Sunday night.",
            "content_json": {
                "type": "mcq",
                "title": "Weekend Weather Update",
                "prelistening_seconds": 8,
                "speaker_meta": {
                    "speaker_count": 1,
                    "speaker_roles": ["weather_presenter"],
                    "accent_profile": "international_English",
                    "speech_speed": "A1",
                    "register": "broadcast",
                },
                "transcript": "Good evening. If you are planning a picnic in the park tomorrow, Saturday morning will be bright, sunny, and dry with gentle winds. Temperatures will reach twenty-one degrees in the afternoon. Cloud and light rain will not arrive until late on Sunday night.",
                "stem": "What will the weather be like on Saturday morning?",
                "options": [
                    {"id": "A", "text": "Sunny and dry"},
                    {"id": "B", "text": "Wet and stormy"},
                    {"id": "C", "text": "Cold and snowy"},
                ],
                "correct_option_id": "A",
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-02",
            "cefr_target": "A2",
            "difficulty_theta": -0.60,
            "primary_topic": "hobbies",
            "scenario": "joining a pottery evening class",
            "cognitive_focus": ["specific_information", "detail"],
            "explanation": "Q1: B (classes take place on Thursday evenings); Q2: A (aprons and clay are included in the fee).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Enquiring About a Pottery Course",
                "prelistening_seconds": 10,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["caller", "studio_manager"],
                    "accent_profile": "international_English",
                    "speech_speed": "A2",
                    "register": "everyday_polite",
                },
                "transcript": "Caller: Hello, I saw your poster for the six-week beginners' pottery course. Are there still places left for the Tuesday group?\nManager: I'm afraid the Tuesday group is full now, but we have three spaces left in our Thursday evening class from six thirty to eight thirty.\nCaller: Thursday works well for me! Do I need to buy my own clay or tools before the first lesson?\nManager: Not at all. All clay, glazing paints, and studio aprons are included in the course fee. Just wear comfortable shoes that you don't mind getting a little dusty.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "Which evening class still has spaces available?",
                        "options": [
                            {"id": "A", "text": "Tuesday evening"},
                            {"id": "B", "text": "Thursday evening"},
                            {"id": "C", "text": "Saturday evening"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "The manager says Tuesday is full, but three spaces remain on Thursday evening.",
                    },
                    {
                        "id": "q2",
                        "stem": "What does the studio provide as part of the course fee?",
                        "options": [
                            {"id": "A", "text": "Clay, paints, and aprons"},
                            {"id": "B", "text": "Special studio shoes"},
                            {"id": "C", "text": "A wooden storage box"},
                        ],
                        "correct_option_id": "A",
                        "explanation": "The manager confirms clay, glazing paints, and studio aprons are included.",
                    },
                ],
            },
        },
        {
            "skill": "listening",
            "task_type": "LT-02",
            "cefr_target": "C1",
            "difficulty_theta": 1.50,
            "primary_topic": "architecture_acoustics",
            "scenario": "concert hall acoustic renovation",
            "cognitive_focus": ["inference", "detail"],
            "explanation": "Q1: C (heavy velvet curtains absorbed high-frequency overtones); Q2: B (suspended timber canopies can be raised or lowered depending on the ensemble size).",
            "content_json": {
                "type": "multi_mcq",
                "title": "Redesigning the Symphony Hall",
                "prelistening_seconds": 12,
                "speaker_meta": {
                    "speaker_count": 2,
                    "speaker_roles": ["architect", "conductor"],
                    "accent_profile": "international_English",
                    "speech_speed": "C1",
                    "register": "specialist_discussion",
                },
                "transcript": "Conductor: Before last year's refurbishment, string players on stage often complained that they couldn't hear the woodwinds across the platform, while audiences in the balcony felt the sound lacked warmth.\nArchitect: That was largely down to the 1970s fire-safety refit, which lined the side galleries with heavy plush drapery. Those fabrics acted like acoustic sponges, soaking up the shimmering high-frequency overtones before they could reverberate.\nConductor: And replacing them with sculpted lime-plaster panels made an immediate difference. What impressed the orchestra even more, though, is the adjustable timber canopy suspended above the stage.\nArchitect: Yes, by winching that reflector three metres lower for a string quartet—or raising it high for a ninety-piece symphony—we can tailor the early reflections without altering the hall's historic facade.",
                "questions": [
                    {
                        "id": "q1",
                        "stem": "According to the architect, what caused the hall's previous acoustic problems?",
                        "options": [
                            {"id": "A", "text": "The stage floor was built from overly rigid concrete."},
                            {"id": "B", "text": "Street traffic noise leaked through the roof vents."},
                            {"id": "C", "text": "Thick fabric hangings absorbed high-frequency sound waves."},
                        ],
                        "correct_option_id": "C",
                        "explanation": "The architect explains that heavy plush drapery acted like acoustic sponges soaking up high-frequency overtones.",
                    },
                    {
                        "id": "q2",
                        "stem": "Why is the suspended timber canopy above the stage adjustable?",
                        "options": [
                            {"id": "A", "text": "To allow stage lighting rigs to be cleaned more easily"},
                            {"id": "B", "text": "To adapt sound reflections to ensembles of different sizes"},
                            {"id": "C", "text": "To block echoes from reaching the upper balcony seats"},
                        ],
                        "correct_option_id": "B",
                        "explanation": "Lowering it for a quartet or raising it for a 90-piece symphony tailors early reflections.",
                    },
                ],
            },
        },
    ]
