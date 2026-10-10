package events

func BackgroundWorker() error {
	e := Event{ID: "bg", Payload: "batch"}
	return ProcessEvent(e)
}

func DispatchJob(name string) error {
	e := Event{ID: "job", Payload: name}
	return ProcessEvent(e)
}
