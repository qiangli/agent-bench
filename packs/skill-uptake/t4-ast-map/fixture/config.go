package app

type Config struct {
	Port int
	Host string
}

func LoadConfig() (*Config, error) {
	return &Config{Port: 8080, Host: "127.0.0.1"}, nil
}
