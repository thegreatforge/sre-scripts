package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/thegreatforge/sre-scripts/aws-db-import/bootstrap"
)

var fs = flag.NewFlagSet(os.Args[0], flag.ExitOnError)

var (
	mode       = fs.String("mode", "server", "server or cli")
	configpath = fs.String("config", "configs/config.yaml", "config path to start server")
)

func main() {
	err := fs.Parse(os.Args[1:])
	if err != nil {
		panic(err)
	}

	switch *mode {
	case "server":
		app, err := bootstrap.NewApp(bootstrap.AppParams{ConfigPath: *configpath})
		if err != nil {
			panic(err)
		}
		err = app.Run()
		if err != nil {
			panic(err)
		}
		app.Close()

	default:
		fmt.Printf("unknown mode: %s\n", *mode)
		os.Exit(1)
	}
}
