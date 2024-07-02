package config

import "github.com/go-playground/validator/v10"

type Config struct {
	Log struct {
		Mode string `yaml:"mode"`
	} `yaml:"log" validate:"required"`
	Server struct {
		Host string `yaml:"host" validate:"required"`
		Port int    `yaml:"port" validate:"required"`
	} `yaml:"server" validate:"required"`
}

func (c Config) Validate() error {
	validate := validator.New(validator.WithRequiredStructEnabled())
	return validate.Struct(c)
}
