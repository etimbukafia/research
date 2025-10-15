;; ============================================
;; ReactRAG Domain - Complete Version
;; A PDDL model of a ReAct agent with RAG capabilities
;; ============================================
(define (domain reactrag)

  (:requirements :strips :typing :negative-preconditions :equality)

  ;; ============================================
  ;; TYPES
  ;; ============================================
  (:types
    role query research-paper web-result information-inventory valid-action answer topic observation verifier - object
  )

  ;; ============================================
  ;; PREDICATES
  ;; ============================================
  (:predicates
    ;; Tool availability
    (has-vectorstore-tool)
    (has-websearch-tool)

    ;; Role states - The agent's role as research assistant
    (role-initialized ?r - role)
    (role-active ?r - role)
    (role-assigned-to-topic ?r - role ?t - topic)

    ;; Query states
    (query-synthesized ?q - query)
    (query-executed-vectorstore ?q - query)
    (query-executed-websearch ?q - query)
    (query-based-on-observation ?q - query ?o - observation)

    ;; Research paper states
    (research-paper-retrieved ?p - research-paper)
    (research-paper-relevant ?p - research-paper ?t - topic)
    (research-paper-analyzed ?p - research-paper)
    (research-paper-cited ?p - research-paper ?a - answer)

    ;; Web result states
    (web-result-retrieved ?w - web-result)
    (web-result-relevant ?w - web-result ?t - topic)
    (web-result-analyzed ?w - web-result)
    (web-result-cited ?w - web-result ?a - answer)

    ;; Information inventory states - The corpus of gathered information
    (information-inventory-initialized ?i - information-inventory)
    (information-inventory-empty ?i - information-inventory)
    (information-inventory-has-content ?i - information-inventory)
    (information-inventory-has-content-from-research-paper ?i - information-inventory ?p - research-paper)
    (information-inventory-has-content-from-web-result ?i - information-inventory ?w - web-result)
    (information-inventory-sufficient ?i - information-inventory)

    ;; Valid action states - Actions the agent can take
    (action-available ?v - valid-action)
    (action-selected ?v - valid-action)
    (action-executed ?v - valid-action)
    (use-vectorstore-tool ?v - valid-action)
    (use-web-research-tool ?v - valid-action)
    (synthesize-information ?v - valid-action)
    (draw-conclusion ?v - valid-action)
    (note-observation ?v - valid-action)
    (provide-answer ?v - valid-action)

    ;; Observation states - What agent notices after each iteration
    (observation-noted ?o - observation)
    (observation-from-research-paper ?o - observation ?p - research-paper)
    (observation-from-web-result ?o - observation ?w - web-result)
    (observation-analyzed ?o - observation)
    (observation-relevant ?o - observation ?t - topic)
    (observation-supports-answer ?o - observation ?a - answer)

    ;; Answer states
    (answer-started ?a - answer)
    (answer-has-sources ?a - answer)
    (answer-complete ?a - answer)
    (answer-verified ?a - answer)
    (answer-has-minimum-sources ?a - answer)
    (answer-based-on-inventory ?a - answer ?i - information-inventory)

    ;; Verifier states - Separate agent that verifies the answer
    (verifier-initialized ?c - verifier)
    (verifier-active ?c - verifier)
    (verifier-received-answer ?c - verifier ?a - answer)
    (verification-in-progress ?c - verifier)
    (verification-passed ?c - verifier ?a - answer)
    (verification-failed ?c - verifier ?a - answer)
    (verification-complete ?c - verifier)

    ;; Topic assignment
    (assigned-topic ?t - topic)
    (topic-researched ?t - topic)

    ;; Reasoning states - Agent's internal reasoning process
    (initialized-role)
    (constraints-understood)
    (information-sufficient)
    (list-premises-explicitly)
    (logical-rule-applied)
    (derived-conclusions)
    (observations-noted)
    (needs-more-research-papers)
    (needs-web-search)

    ;; Counters (simplified boolean version)
    (has-at-least-two-sources ?a - answer)
    (has-at-least-three-research-papers ?i - information-inventory)
  )

  ;; ============================================
  ;; ACTIONS
  ;; ============================================

  ;; Action: Initialize the agent's role
  (:action initialize-role
    :parameters (?r - role ?t - topic)
    :precondition (and
      (assigned-topic ?t)
      (not (role-initialized ?r))
      (not (initialized-role))
    )
    :effect (and
      (role-initialized ?r)
      (role-active ?r)
      (role-assigned-to-topic ?r ?t)
      (initialized-role)
      (constraints-understood)
    )
  )

  ;; Action: Initialize information inventory
  (:action initialize-information-inventory
    :parameters (?i - information-inventory ?r - role)
    :precondition (and
      (role-initialized ?r)
      (not (information-inventory-initialized ?i))
    )
    :effect (and
      (information-inventory-initialized ?i)
      (information-inventory-empty ?i)
    )
  )

  ;; Action: Synthesize query for research
  (:action synthesize-query
    :parameters (?q - query ?t - topic ?r - role)
    :precondition (and
      (role-active ?r)
      (assigned-topic ?t)
      (role-assigned-to-topic ?r ?t)
      (not (query-synthesized ?q))
    )
    :effect (and
      (query-synthesized ?q)
    )
  )

  ;; Action: Select action to use vectorstore
  (:action select-use-vectorstore
    :parameters (?v - valid-action ?q - query)
    :precondition (and
      (has-vectorstore-tool)
      (query-synthesized ?q)
      (not (action-selected ?v))
      (action-available ?v)
    )
    :effect (and
      (action-selected ?v)
      (use-vectorstore-tool ?v)
    )
  )

  ;; Action: Search vectorstore for papers
  (:action search-vectorstore
    :parameters (?q - query ?t - topic ?v - valid-action)
    :precondition (and
      (has-vectorstore-tool)
      (query-synthesized ?q)
      (assigned-topic ?t)
      (use-vectorstore-tool ?v)
      (action-selected ?v)
      (not (query-executed-vectorstore ?q))
    )
    :effect (and
      (query-executed-vectorstore ?q)
      (action-executed ?v)
    )
  )

  ;; Action: Retrieve paper from vectorstore results
  (:action retrieve-research-paper
    :parameters (?p - research-paper ?q - query ?t - topic ?i - information-inventory)
    :precondition (and
      (query-executed-vectorstore ?q)
      (assigned-topic ?t)
      (information-inventory-initialized ?i)
      (not (research-paper-retrieved ?p))
    )
    :effect (and
      (research-paper-retrieved ?p)
      (research-paper-relevant ?p ?t)
      (information-inventory-has-content ?i)
      (information-inventory-has-content-from-research-paper ?i ?p)
      (not (information-inventory-empty ?i))
    )
  )

  ;; Action: Create observation from research paper
  (:action observe-from-research-paper
    :parameters (?o - observation ?p - research-paper ?t - topic ?v - valid-action)
    :precondition (and
      (research-paper-retrieved ?p)
      (research-paper-relevant ?p ?t)
      (not (observation-noted ?o))
      (action-available ?v)
    )
    :effect (and
      (observation-noted ?o)
      (observation-from-research-paper ?o ?p)
      (observation-relevant ?o ?t)
      (note-observation ?v)
      (action-selected ?v)
      (observations-noted)
    )
  )

  ;; Action: Analyze a retrieved paper based on observation
  (:action analyze-research-paper
    :parameters (?p - research-paper ?t - topic ?o - observation)
    :precondition (and
      (research-paper-retrieved ?p)
      (research-paper-relevant ?p ?t)
      (observation-noted ?o)
      (observation-from-research-paper ?o ?p)
      (not (research-paper-analyzed ?p))
    )
    :effect (and
      (research-paper-analyzed ?p)
      (observation-analyzed ?o)
      (list-premises-explicitly)
    )
  )

  ;; Action: Select action to use web search
  (:action select-use-web-search
    :parameters (?v - valid-action ?q - query)
    :precondition (and
      (has-websearch-tool)
      (query-synthesized ?q)
      (not (action-selected ?v))
      (action-available ?v)
    )
    :effect (and
      (action-selected ?v)
      (use-web-research-tool ?v)
    )
  )

  ;; Action: Search the web
  (:action search-web
    :parameters (?q - query ?t - topic ?v - valid-action)
    :precondition (and
      (has-websearch-tool)
      (query-synthesized ?q)
      (assigned-topic ?t)
      (use-web-research-tool ?v)
      (action-selected ?v)
      (not (query-executed-websearch ?q))
    )
    :effect (and
      (query-executed-websearch ?q)
      (action-executed ?v)
    )
  )

  ;; Action: Retrieve web result
  (:action retrieve-web-result
    :parameters (?w - web-result ?q - query ?t - topic ?i - information-inventory)
    :precondition (and
      (query-executed-websearch ?q)
      (assigned-topic ?t)
      (information-inventory-initialized ?i)
      (not (web-result-retrieved ?w))
    )
    :effect (and
      (web-result-retrieved ?w)
      (web-result-relevant ?w ?t)
      (information-inventory-has-content ?i)
      (information-inventory-has-content-from-web-result ?i ?w)
      (not (information-inventory-empty ?i))
    )
  )

  ;; Action: Create observation from web result
  (:action observe-from-web-result
    :parameters (?o - observation ?w - web-result ?t - topic ?v - valid-action)
    :precondition (and
      (web-result-retrieved ?w)
      (web-result-relevant ?w ?t)
      (not (observation-noted ?o))
      (action-available ?v)
    )
    :effect (and
      (observation-noted ?o)
      (observation-from-web-result ?o ?w)
      (observation-relevant ?o ?t)
      (note-observation ?v)
      (action-selected ?v)
      (observations-noted)
    )
  )

  ;; Action: Analyze web result based on observation
  (:action analyze-web-result
    :parameters (?w - web-result ?t - topic ?o - observation)
    :precondition (and
      (web-result-retrieved ?w)
      (web-result-relevant ?w ?t)
      (observation-noted ?o)
      (observation-from-web-result ?o ?w)
      (not (web-result-analyzed ?w))
    )
    :effect (and
      (web-result-analyzed ?w)
      (observation-analyzed ?o)
      (list-premises-explicitly)
    )
  )

  ;; Action: Synthesize information from inventory
  (:action synthesize-information-from-inventory
    :parameters (?i - information-inventory ?v - valid-action ?t - topic)
    :precondition (and
      (information-inventory-has-content ?i)
      (observations-noted)
      (list-premises-explicitly)
      (assigned-topic ?t)
      (action-available ?v)
    )
    :effect (and
      (synthesize-information ?v)
      (action-selected ?v)
      (logical-rule-applied)
      (derived-conclusions)
    )
  )

  ;; Action: Determine if information is sufficient
  (:action verify-information-sufficiency
    :parameters (?i - information-inventory)
    :precondition (and
      (information-inventory-has-content ?i)
      (logical-rule-applied)
      (derived-conclusions)
    )
    :effect (and
      (information-inventory-sufficient ?i)
      (information-sufficient)
    )
  )

  ;; Action: Start composing answer
  (:action start-answer
    :parameters (?a - answer ?t - topic ?i - information-inventory ?v - valid-action)
    :precondition (and
      (assigned-topic ?t)
      (information-inventory-sufficient ?i)
      (information-sufficient)
      (action-available ?v)
      (not (answer-started ?a))
    )
    :effect (and
      (answer-started ?a)
      (answer-based-on-inventory ?a ?i)
      (provide-answer ?v)
      (action-selected ?v)
    )
  )

  ;; Action: Cite a research paper in answer with observation support
  (:action cite-research-paper
    :parameters (?p - research-paper ?a - answer ?t - topic ?o - observation)
    :precondition (and
      (answer-started ?a)
      (research-paper-analyzed ?p)
      (research-paper-relevant ?p ?t)
      (observation-analyzed ?o)
      (observation-from-research-paper ?o ?p)
      (not (research-paper-cited ?p ?a))
    )
    :effect (and
      (research-paper-cited ?p ?a)
      (observation-supports-answer ?o ?a)
      (answer-has-sources ?a)
    )
  )

  ;; Action: Cite web result in answer with observation support
  (:action cite-web-result
    :parameters (?w - web-result ?a - answer ?t - topic ?o - observation)
    :precondition (and
      (answer-started ?a)
      (web-result-analyzed ?w)
      (web-result-relevant ?w ?t)
      (observation-analyzed ?o)
      (observation-from-web-result ?o ?w)
      (not (web-result-cited ?w ?a))
    )
    :effect (and
      (web-result-cited ?w ?a)
      (observation-supports-answer ?o ?a)
      (answer-has-sources ?a)
    )
  )

  ;; Action: Verify sufficient sources (simplified)
  (:action verify-sufficient-sources
    :parameters (?a - answer)
    :precondition (and
      (answer-started ?a)
      (answer-has-sources ?a)
    )
    :effect (and
      (answer-has-minimum-sources ?a)
      (has-at-least-two-sources ?a)
    )
  )

  ;; Action: Mark topic as researched
  (:action mark-topic-researched
    :parameters (?t - topic ?r - role)
    :precondition (and
      (assigned-topic ?t)
      (role-assigned-to-topic ?r ?t)
      (information-sufficient)
    )
    :effect (and
      (topic-researched ?t)
    )
  )

  ;; Action: Complete answer
  (:action complete-answer
    :parameters (?a - answer ?t - topic)
    :precondition (and
      (answer-started ?a)
      (answer-has-minimum-sources ?a)
      (information-sufficient)
      (topic-researched ?t)
    )
    :effect (and
      (answer-complete ?a)
    )
  )

  ;; Action: Initialize verifier
  (:action initialize-verifier
    :parameters (?c - verifier ?a - answer)
    :precondition (and
      (answer-complete ?a)
      (not (verifier-initialized ?c))
    )
    :effect (and
      (verifier-initialized ?c)
      (verifier-active ?c)
    )
  )

  ;; Action: Verifier receives answer
  (:action verifier-receive-answer
    :parameters (?c - verifier ?a - answer)
    :precondition (and
      (verifier-active ?c)
      (answer-complete ?a)
      (not (verifier-received-answer ?c ?a))
    )
    :effect (and
      (verifier-received-answer ?c ?a)
      (verification-in-progress ?c)
    )
  )

  ;; Action: Verifier verifies answer against query and sources
  (:action verify-answer
    :parameters (?c - verifier ?a - answer ?t - topic)
    :precondition (and
      (verifier-received-answer ?c ?a)
      (verification-in-progress ?c)
      (answer-has-minimum-sources ?a)
      (assigned-topic ?t)
    )
    :effect (and
      (verification-passed ?c ?a)
      (answer-verified ?a)
      (verification-complete ?c)
    )
  )
)