import unittest
from unittest.mock import patch, Mock, MagicMock, call
from app.api.routes.users.schemas import UserDTO
from app.api.routes.cards.schemas import CardDTO  
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from app.core.models import Card
from fastapi import HTTPException
from app.api.routes.cards.service import (
                                        unique_card_number, 
                                        create_cvv_number, 
                                        create_card_number, 
                                        create_expiration_date, 
                                        get_user_fullname,
                                        get_card_by_id,
                                        delete
                                        )

def fake_card():
    return Card(
        account_id=1,
        card_number= "1111222233334444",
        expiration_date= "2024-02-02",
        card_holder= "Dimitar Berbatov",
        cvv= "123"
    )

def fake_card_dto():
    return CardDTO(
        id=1,
        account_id=1,
        card_number= "1111222233334444",
        expiration_date= "2024-02-02",
        card_holder= "Dimitar Berbatov",
        cvv= "123"
    )

def fake_user_view():
    return UserDTO(
        username="testuser", 
        password="User!234",
        phone_number="1234567891",
        email="email@email.com",
        fullname="Georgi Stoev"
    )

Session = sessionmaker()


def fake_db():
    session_mock = Mock(spec=Session)
    session_mock.query = Mock()
    session_mock.query.filter = Mock()
    return session_mock

class CardsServiceShould(unittest.TestCase):

    @patch("app.api.routes.cards.service.random.choice")
    def test_createCardNumber_IsCorrect(self, create_mock):
        # Arrange
        create_mock.side_effect = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '1', '2', '3', '4', '5', '6']

        # Act
        result = create_card_number()

        # Assert
        self.assertEqual(result, '1234567890123456')
        self.assertEqual(len(result), 16)
        create_mock.assert_called_with('0123456789')
        self.assertEqual(create_mock.call_count, 16)


    @patch("app.api.routes.cards.service.datetime")
    def test_createExpirationDate_IsCorrect(self, datetime_mock):
        #Arrange
        fixed_time_now = datetime(2024,1,1)
        datetime_mock.now.return_value = fixed_time_now
        datetime_mock.timedelta = timedelta

        # Act 
        result = create_expiration_date()

        #Assert
        expected_date = fixed_time_now + timedelta(days=1826)
        self.assertEqual(expected_date, result)
        
    @patch('app.api.routes.cards.service.random.choice')
    def test_generateCvv_IsCorrectFormat(self, mock_random_choice):
        # Arrange
        mock_random_choice.side_effect = lambda x: x[0] 

        # Act 
        result = create_cvv_number()

        # Assert
        self.assertTrue(result.isdigit())  
        self.assertEqual(len(result), 3)   
        mock_random_choice.assert_called_with('0123456789')  
        self.assertEqual(mock_random_choice.call_count, 3)   

    @patch('app.api.routes.cards.service.create_card_number')
    @patch('app.api.routes.cards.service.get_db')
    def test_createCardNumber_createsUniqueCardNumber(self, mock_get_db, mock_create_card_number):
        # Arrange
        mock_db_session = fake_db()
        mock_get_db.return_value = mock_db_session

        def filter_by_side_effect(card_number):
            filter_mock = Mock()
            filter_mock.first.return_value = None
            return filter_mock

        mock_query = mock_db_session.query.return_value
        mock_query.filter_by.side_effect = filter_by_side_effect

        mock_create_card_number.side_effect = ['1234567890123456', '2345678901234567', '3456789012345678']

        # Act
        result1 = unique_card_number(mock_db_session)
        result2 = unique_card_number(mock_db_session)
        result3 = unique_card_number(mock_db_session)

        # Assert
        assert result1 == '1234567890123456'
        assert result2 == '2345678901234567'
        assert result3 == '3456789012345678'

        # Verify mock calls
        mock_create_card_number.assert_called()
        assert mock_create_card_number.call_count == 3
        mock_db_session.query.assert_called_with(Card)
        mock_query.filter_by.assert_has_calls([
            call(card_number='1234567890123456'),
            call(card_number='2345678901234567'),
            call(card_number='3456789012345678')
        ], any_order=True)
        assert mock_query.filter_by.call_count == 3



    def test_getUserFullName_returnsCorrectName(self):
        # Arrange
        mock_db_session = fake_db()

        mock_user = fake_user_view()
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        mock_current_user = fake_user_view()

        # Act
        result = get_user_fullname(mock_current_user, mock_db_session)

        # Assert
        self.assertEqual(mock_user, result)

        # Verify mock calls
        mock_db_session.query.assert_called_once()  
        mock_db_session.query.return_value.filter_by.assert_called_once_with(username=mock_current_user.username)
        mock_db_session.query.return_value.filter_by.return_value.first.assert_called_once()


    @patch('app.api.routes.cards.service.get_db')
    def test_getCardById_returnsTheCardSuccessfully(self, mock_get_db):
        # Arrange
        expected_card = fake_card() 

        db = fake_db()
        mock_get_db.return_value = db
        db.query(Card).filter_by(id=expected_card.id).first.return_value = expected_card

        # Act
        actual_card = get_card_by_id(expected_card.id, db)

        # Assert
        self.assertEqual(actual_card, expected_card)


    @patch('app.api.routes.cards.service.get_db')
    def test_getCardById_returnsReturnsHTTPExceptionWhenNotFound(self, mock_get_db):
        # Arrange
        card_id = 12231  
        db = fake_db()
        mock_get_db.return_value = db
        db.query(Card).filter_by(id=card_id).first.return_value = None

        # Act
        try:
            get_card_by_id(card_id, db)
            self.fail("Expected HTTPException not raised.")
        except HTTPException as e:
        
        # Assert
            self.assertEqual(e.status_code, 404)
            self.assertEqual(e.detail, "Card not found!")


    @patch('app.api.routes.cards.service.get_card_by_id')
    @patch('app.api.routes.cards.service.get_db')
    def test_deleteCard_trulyDeleted(self, mock_get_db, mock_get_card_by_id):
        # Arrange
        card = fake_card_dto()
        db = fake_db()
        db.delete = Mock()
        db.commit = Mock()
        mock_get_db.return_value = db

        card_to_delete = Mock(spec=Card)
        mock_get_card_by_id.return_value = card_to_delete

        # Act
        delete(card.id, db)

        # Assert
        mock_get_card_by_id.assert_called_once_with(card.id, db)
        db.delete.assert_called_once_with(card_to_delete)
        db.commit.assert_called_once()