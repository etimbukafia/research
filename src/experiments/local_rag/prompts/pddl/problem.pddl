;; ============================================
;; ReactRAG Problem - Example Instance
;; ============================================

(define (problem reactrag-problem-1)
	(:domain reactrag)

	;; ============================================
	;; OBJECTS
	;; ============================================
	(:objects
		role1 - role
		topic1 - topic
		query1 - query
		paper1 paper2 paper3 - research-paper
		web1 web2 - web-result
		inventory1 - information-inventory
		action1 action2 action3 action4 action5 action6 - valid-action
		obs1 obs2 obs3 obs4 - observation
		ans1 - answer
		verifier1 - verifier
	)

	;; ============================================
	;; INITIAL STATE
	;; ============================================
	(:init
		;; Tools available
		(has-vectorstore-tool)
		(has-websearch-tool)

		;; Role not yet initialized
		(not (initialized-role))

		;; Assigned topic
		(assigned-topic topic1)

		;; Valid actions available
		(action-available action1)
		(action-available action2)
		(action-available action3)
		(action-available action4)
		(action-available action5)
		(action-available action6)

		;; No information yet
		(not (information-inventory-initialized inventory1))
		(not (information-inventory-has-content inventory1))

		;; No queries or research yet
		(not (query-synthesized query1))
		(not (query-executed-vectorstore query1))
		(not (query-executed-websearch query1))

		;; No papers retrieved or analyzed
		(not (research-paper-retrieved paper1))
		(not (research-paper-retrieved paper2))
		(not (research-paper-retrieved paper3))

		;; No web results retrieved
		(not (web-result-retrieved web1))
		(not (web-result-retrieved web2))

		;; No answer yet
		(not (answer-started ans1))
		(not (answer-complete ans1))
		(not (answer-verified ans1))

		;; Verifier not yet active
		(not (verifier-initialized verifier1))
	)

	;; ============================================
	;; GOAL
	;; ============================================
	(:goal
		(and
			;; Agent’s role is active and assigned to the topic
			(role-active role1)
			(role-assigned-to-topic role1 topic1)

			;; Query has been synthesized and executed
			(query-synthesized query1)
			(query-executed-vectorstore query1)
			(query-executed-websearch query1)

			;; Information inventory has been built and sufficient
			(information-inventory-sufficient inventory1)

			;; At least one paper and one web result analyzed
			(research-paper-analyzed paper1)
			(web-result-analyzed web1)

			;; Observations noted and conclusions derived
			(derived-conclusions)
			(information-sufficient)

			;; Final answer complete and verified
			(answer-complete ans1)
			(answer-verified ans1)
		)
	)
)