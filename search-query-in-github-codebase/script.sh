#!/bin/bash

# Set your GitHub access token
TOKEN="${TOKEN}"

# Set the organization and search query
ORG="${GITHUB_ORG}"
QUERY="${QUERY}"

# Search code in all repositories belonging to the organization
results=$(curl -s -H "Authorization: token $TOKEN" "https://api.github.com/search/code?q=$QUERY+org:$ORG&per_page=100")

# Loop through the results and print the repository name and file path
for result in $(echo "${results}" | jq -r '.items[].repository.full_name'); do
  echo $result
done
