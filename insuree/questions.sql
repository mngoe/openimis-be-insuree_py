-- use IMIS
 insert into tblQuestions (code, Question, AltLanguage, QuestionType) VALUES (
'earn_amount', 'Combien gagnez-vous en moyenne? (montant / mois en CFA)', 'How much do you earn on average? (amount per month in CFA)', 'Dropdown'
 ),
 ('health_status', 'Souffrant de toute maladie chronique', 'Suffering from any chronic', 'Checkbox'),
 ('nutrition_status', 'Nombre de repas par jour', 'Nutrition status', 'Dropdown'),
 ('nb_person_living', 'Nombre de personnes vivant a la maison', 'Nomber of persons living in the house', 'Text'),
 ('nb_rooms', 'Nombre de chambres', 'Nomber of rooms', 'Text'),
 ('f_support', 'Quel type de soutien recevez-vous de la part d''une organisation?', 'Which type of food support are you receiveing from any organization?', 'Dropdown'),
 ('m_support', 'Quel type de soutien matériel recevez-vous de la part d''une organisation?', 'Which type of material support are you receiveing from any organization?', 'Dropdown'),
 ('h_support', 'Quel type de soins de santé maternelle et autre soutient sanitaire recevez-vous de la part d''une organisation quelconque?', 'Which type of maternal health care and other health support are you receiving from any origanization?', 'Dropdown'),
 ('displacement_cond', 'Conditions de déplacement', 'Displacement conditions', 'Dropdown')

insert into tblOptions (code, Options, OptionMark, AltLanguage, SortOrder, Question) VALUES
 ('0_15000', '0-15 000', 4, '0-15 000', 1, 1),
 ('15001_30000', '15 001-30 000', 4, '15 001-30 000', 2, 1),
 ('30001_65000', '30 001-65 000', 3, '30 001-65 000', 3, 1),
 ('65001_140000', '65 001-140 000', 2, '65 001-140 000', 4, 1),
 ('140001_330000', '140 000-330 000', 1, '140 000-330 000', 5, 1),
 ('330001_1000000', '330 000-1 000 000', 0, '330 000-1 000 000', 6, 1),
 ('1000000+', '1 000 000+', 0, '1 000 000+', 7, 1),
 ('yes', 'Oui', 5, 'Yes', 8, 2),
 ('no', 'Non', 1, 'Non', 9, 2),
 ('0_1', '0 a 1', 10, '0 to 1', 10, 3),
 ('2_3', '2 a 3', 5, '2 a 3', 11, 3),
 ('3+', '3+', 1, '3+', 12, 3),
 ('r_f', 'Régulier', 1, 'Regular', 13, 6),
 ('i_f', 'Irégulier', 2, 'Iregular', 14, 6),
 ('n_f', 'Aucun', 3, 'None', 15, 6),
 ('r_m', 'Régulier', 1, 'Regular', 16, 7),
 ('i_m', 'Irégulier', 2, 'Iregular', 17, 7),
 ('n_m', 'Aucun', 3, 'None', 18, 7),
 ('r_h', 'Régulier', 1, 'Regular', 19, 8),
 ('i_h', 'Irégulier', 3, 'Iregular', 20, 8),
 ('n_h', 'Aucun', 5, 'None', 21, 8),
 ('loss_of_property_and_livelihood', 'Perte de biens et de moyen de subsistance', 15, 'Loss of property and livelihood', 22, 9),
 ('loss_of_livelihood', 'Perte de moyen de subsistance', 14, 'Loss of livelihood', 23, 9),
 ('loss_of_property', 'Perte de biens', 13, 'Loss of property', 24, 9),
 ('loss_of_none', 'Aucun', 10, 'None', 25, 9)
