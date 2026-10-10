package app

type Server struct {
	cfg    *Config
	router *Router
}

func NewServer(cfg *Config, router *Router) *Server {
	return &Server{cfg: cfg, router: router}
}

func (s *Server) Start() error {
	return nil
}

func (s *Server) Stop() error {
	return nil
}
