PROJECTNAME=$(shell basename $(PWD))

# Make is verbose in Linux. Made it silent
MAKEFLAGS += --silent

## usage: make [option]
## Options:
.PHONY : help
help : Makefile
	echo "\n$(PROJECTNAME)"
	echo "The project $(PROJECTNAME) is to selective write exports of aws databases from s3 to their original database\n"
	sed -n 's/^## //p' $<
	sed -n 's/^###/ 🔖/p' $<

### exec: To execute the project without building - `make exec` 
.PHONY: exec
exec:
	go run main.go