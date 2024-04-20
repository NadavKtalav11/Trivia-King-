import random

class Questions:
    def __init__(self):
        """self.questions_answers = [
            ("Is the Eiffel Tower taller during the summer due to thermal expansion?", True),
            ("Did Cleopatra VII speak nine languages fluently?", True),
            ("Was the Great Wall of China visible from space without aid?", False),
            ("Is Mount Everest the tallest mountain above sea level?", True),
            ("Did Leonardo da Vinci invent scissors?", False),
            ("Did Vikings wear horned helmets in battle?", False),
            ("Was the first computer virus created in 1986?", True),
            ("Is the Sahara Desert larger than the entire continental United States?", True),
            ("Were dinosaurs the largest animals to ever roam the Earth?", True),
            ("Did Marie Curie win Nobel Prizes in two different scientific fields?", True),
            ("Is the human brain fully developed by the age of five?", False),
            ("Were fortune cookies invented in China?", False),
            ("Did Queen Elizabeth I of England never marry?", False),
            ("Is the tongue the strongest muscle in the human body?", False),
            ("Did ancient Romans use urine as mouthwash?", True),
            ("Is Iceland covered in ice and Greenland covered in greenery?",False),
            ("Were there no female pharaohs in ancient Egypt?", False),
            ("Did Shakespeare write all of his plays alone?", False),
            ("Is the moon slowly moving away from Earth?", True),
            ("Were tomatoes once considered poisonous in Europe?", True)
        ]"""
        
        self.questions_answers = [
            ("Is the Eiffel Tower taller during the summer due to thermal expansion?", True),
            ("Did Cleopatra VII speak nine languages fluently?", True),
            ("Was the Great Wall of China visible from space without aid?", False)
        ]
        self.used_questions = []

    def get_questions(self):
        return [q[0] for q in self.questions_answers]

    def get_answers(self):
        return [q[1] for q in self.questions_answers]

    def get_question_answer_pairs(self):
        return self.questions_answers

    def get_random_question(self):
        remaining_questions = [q for q in self.questions_answers if q[0] not in self.used_questions]
        if not remaining_questions:
            # Reset used questions if all questions have been used
            self.used_questions = []
            remaining_questions = self.questions_answers

        question, answer = random.choice(remaining_questions)
        self.used_questions.append(question)
        return question, answer

    def no_repeated_questions_remaining(self):
        return len(self.used_questions) == len(self.questions_answers)



