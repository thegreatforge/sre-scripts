package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"text/template"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ssm"
)

var (
	ErrorLogger          *log.Logger
	ssmPaths             ssmPathsSlice
	ssmOptWithDecryption bool  = true
	ssmOptMaxResults     int64 = 10
	ssmOptNextToken      string
)

func init() {
	ErrorLogger = log.New(os.Stderr, "ERROR ", log.Ldate|log.Ltime|log.Lshortfile)
}

type ssmPathsSlice []string

func (i *ssmPathsSlice) Set(value string) error {
	*i = append(*i, value)
	return nil
}

func (i *ssmPathsSlice) String() string {
	return ""
}

func main() {
	awsProfile := flag.String("profile", "", "AWS profile")
	awsRegion := flag.String("region", "", "AWS Region")
	flag.Var(&ssmPaths, "path", "SSM Parameter path")
	goTemplate := flag.String("template", "", "if specified, renders custom output from a template file")

	flag.Parse()

	sessOpt := session.Options{
		SharedConfigState: session.SharedConfigEnable,
	}

	if *awsProfile != "" {
		sessOpt = session.Options{
			Profile: *awsProfile,
			Config:  aws.Config{Region: aws.String(*awsRegion)},
		}
	}

	sess, err := session.NewSessionWithOptions(sessOpt)

	if err != nil {
		ErrorLogger.Fatalf("Unable to create the aws session - %s", err)
	}

	svc := ssm.New(sess)
	output := make(map[string]string)

	for _, ssmPath := range ssmPaths {
		ssmOpts := ssm.GetParametersByPathInput{
			Path:           &ssmPath,
			WithDecryption: &ssmOptWithDecryption,
			MaxResults:     &ssmOptMaxResults,
		}

		for {
			if ssmOptNextToken != "" {
				ssmOpts.NextToken = &ssmOptNextToken
			}

			resp, err := svc.GetParametersByPath(&ssmOpts)
			if err != nil {
				ErrorLogger.Fatal(err)
			}

			for _, parameter := range resp.Parameters {
				s := strings.Split(*parameter.Name, "/")
				key := s[len(s)-1]
				output[key] = *parameter.Value
			}

			if resp.NextToken != nil {
				ssmOptNextToken = *resp.NextToken
			} else {
				ssmOptNextToken = ""
				break
			}
		}
	}

	if *goTemplate != "" {
		t, err := template.ParseFiles(*goTemplate)
		if err != nil {
			ErrorLogger.Fatal(err)
		}
		t.Execute(os.Stdout, output)
	} else {
		jsonString, err := json.MarshalIndent(output, "", "  ")
		if err != nil {
			ErrorLogger.Fatal(err)
		}

		fmt.Println(string(jsonString))
	}
}
