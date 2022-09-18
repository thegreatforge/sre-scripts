provider "aws" {
  region = "ap-south-1"
}

terraform {
  required_version = ">= 0.13"
  required_providers {
    aws = {
      version = "~> 4.5.0"
    }
  }
}
