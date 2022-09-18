PROJECTNAME=$(shell basename $(PWD))
# Make is verbose in Linux. Made it silent
MAKEFLAGS += --silent

## usage: make [option]
## Options:
.PHONY : help
help : Makefile
	echo "Choose a command run in $(PROJECTNAME):"
	sed -n 's/^## //p' $<
	sed -n 's/^###/ /p' $<

### build-linux: To build the linux binary distro
.PHONY: build-linux
build-linux:
	docker build --build-arg GOOS="linux" --no-cache -f Dockerfile -t ssm-template:latest --output type=local,dest=bin .


### build-darwin: To build the darwin binary 
.PHONY: build-darwin
build-darwin:
	docker build --build-arg GOOS="darwin" --no-cache -f Dockerfile -t ssm-template:latest --output type=local,dest=bin .
