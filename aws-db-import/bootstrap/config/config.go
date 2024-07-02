package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

var Data Config

func InitConfig(configPath string) (Config, error) {
	configFile, err := os.ReadFile(configPath)
	if err != nil {
		return Data, err
	}

	err = yaml.Unmarshal(configFile, &Data)
	if err != nil {
		return Data, err
	}

	if err = Data.Validate(); err != nil {
		return Data, err
	}
	return Data, nil
}
