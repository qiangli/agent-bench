package events

type Event struct {
	ID      string
	Payload string
}

func ProcessEvent(e Event) error {
	return nil
}
