package app

type Router struct {
	routes map[string]string
}

func NewRouter() *Router {
	return &Router{routes: make(map[string]string)}
}

func (r *Router) RegisterRoute(path string, handler string) {
	r.routes[path] = handler
}
