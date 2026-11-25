.PHONY: staging-up staging-down staging-deploy staging-status

staging-up:      ## create staging (~25 min)
	@bash scripts/staging.sh up

staging-down:    ## destroy staging, keep the state bucket (~15 min)
	@bash scripts/staging.sh down

staging-deploy:  ## build + push the 4 images, helm install (needs Docker running)
	@bash scripts/staging.sh deploy

staging-status:  ## read-only: is anything still billing?
	@bash scripts/staging.sh status
