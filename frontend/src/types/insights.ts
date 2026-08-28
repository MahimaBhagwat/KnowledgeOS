export interface Flashcard {
  question: string;
  answer: string;
}

export interface DocumentInsights {
  document_id: string;
  summary: string;
  key_takeaways: string[];
  flashcards: Flashcard[];
}
