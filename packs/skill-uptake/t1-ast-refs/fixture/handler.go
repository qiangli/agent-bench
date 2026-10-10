package events

func HandleWebhook(payload string) error {
	e := Event{ID: "webhook", Payload: payload}
	return ProcessEvent(e)
}

func HandleCron() error {
	return nil
}
