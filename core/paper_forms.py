# -*- coding: utf-8 -*-
from django.db.models import FieldDoesNotExist
from ecs.core.models import SubmissionForm

SUBMISSION_SECTION_DATA = [
    ('1.', u'Allgemeines'),
    ('2.', u'Eckdaten der Studie'),
    ('3a', u'Betrifft nur Studien gemäß AMG: Angaben zur Prüfsubstanz (falls nicht in Österreich registriert):'),
]

_submission_field_data = (
    ('1.1', 'project_title'),
    ('1.2', None), #'protocol_number'
    ('1.3', None), #'date_of_protocol'
    ('1.2.1', 'eudract_number'),
    ('1.3.1', None), #'isrctn_number'
    ('1.5.1', 'sponsor_name'),
    ('1.5.3', 'sponsor_contactname'),
    ('1.5.2', 'sponsor_address1'),
    ('1.5.2', 'sponsor_address2'),
    ('1.5.2', 'sponsor_zip_code'),
    ('1.5.2', 'sponsor_city'),
    ('1.5.4', 'sponsor_phone'),
    ('1.5.5', 'sponsor_fax'),
    ('1.5.6', 'sponsor_email'),
    ('1.5.1', 'invoice_name'),
    ('1.5.3', 'invoice_contactname'),
    ('1.5.2', 'invoice_address1'),
    ('1.5.2', 'invoice_address2'),
    ('1.5.2', 'invoice_zip_code'),
    ('1.5.2', 'invoice_city'),
    ('1.5.4', 'invoice_phone'),
    ('1.5.5', 'invoice_fax'),
    ('1.5.6', 'invoice_email'),
    ('1.5.7', 'invoice_uid'),
    (None, 'invoice_uid_verified_level1'),
    (None, 'invoice_uid_verified_level2'),
    ('2.1.1', 'project_type_non_reg_drug'),
    ('2.1.2', 'project_type_reg_drug'),
    ('2.1.2.1', 'project_type_reg_drug_within_indication'),
    ('2.1.2.2', 'project_type_reg_drug_not_within_indication'),
    ('2.1.3', 'project_type_medical_method'),
    ('2.1.4', 'project_type_medical_device'),
    ('2.1.4.1', 'project_type_medical_device_with_ce'),
    ('2.1.4.2', 'project_type_medical_device_without_ce'),
    ('2.1.4.3', 'project_type_medical_device_performance_evaluation'),
    ('2.1.5', 'project_type_basic_research'),
    ('2.1.6', 'project_type_genetic_study'),
    ('2.1.7', 'project_type_register'), # new
    ('2.1.8', 'project_type_biobank'), # new
    ('2.1.9', 'project_type_retrospective'), # new
    ('2.1.10', 'project_type_questionnaire'), # new
    ('2.1.11', 'project_type_misc'), # was: 2.17
    ('2.1.12', 'project_type_education_context'), # was: 2.1.8 + 2.1.9
    ('2.2', 'specialism'),
    ('2.3.1', 'pharma_checked_substance'),
    ('2.3.2', 'pharma_reference_substance'),
    ('2.4.1', 'medtech_checked_product'),
    ('2.4.2', 'medtech_reference_substance'),
    ('2.5', 'clinical_phase'),
    ('2.8', 'already_voted'),
    ('2.9', 'subject_count'),
    ('2.10.1', 'subject_minage'),
    ('2.10.2', 'subject_maxage'),
    ('2.10.3', 'subject_noncompetents'),
    ('2.10.4', 'subject_males'),
    ('2.10.4', 'subject_females'),
    ('2.10.5', 'subject_childbearing'),
    ('2.11', 'subject_duration'),
    ('2.11.1', 'subject_duration_active'),
    ('2.11.2', 'subject_duration_controls'),
    ('2.12', 'subject_planned_total_duration'),
    ('3.1', 'substance_registered_in_countries'),
    ('3.2', 'substance_preexisting_clinical_tries'),
    ('3.2.1', 'substance_p_c_t_countries'),
    ('3.2.2', 'substance_p_c_t_phase'),
    ('3.2.3', 'substance_p_c_t_period'),
    ('3.2.4', 'substance_p_c_t_application_type'),
    ('3.2.5', 'substance_p_c_t_gcp_rules'),
    ('3.2.6', 'substance_p_c_t_final_report'),
    ('4.1', 'medtech_product_name'),
    ('4.2', 'medtech_manufacturer'),
    ('4.3', 'medtech_certified_for_exact_indications'),
    ('4.4', 'medtech_certified_for_other_indications'),
    ('4.5', 'medtech_ce_symbol'),
    ('4.6', 'medtech_manual_included'),
    ('4.7', 'medtech_technical_safety_regulations'),
    ('4.8', 'medtech_departure_from_regulations'),
    ('5.1.1', 'insurance_name'),
    ('5.1.2', 'insurance_address_1'),
    ('5.1.3', 'insurance_phone'),
    ('5.1.4', 'insurance_contract_number'),
    ('5.1.5', 'insurance_validity'),
    ('6.3', 'additional_therapy_info'),
    ('7.1', 'german_project_title'),
    ('7.2', 'german_summary'),
    ('7.3', 'german_preclinical_results'),
    ('7.4', 'german_primary_hypothesis'),
    ('7.5', 'german_inclusion_exclusion_crit'),
    ('7.6', 'german_ethical_info'),
    ('7.7', 'german_protected_subjects_info'),
    ('7.8', 'german_recruitment_info'),
    ('7.9', 'german_consent_info'),
    ('7.10', 'german_risks_info'),
    ('7.11', 'german_benefits_info'),
    ('7.12', 'german_relationship_info'),
    ('7.13', 'german_concurrent_study_info'),
    ('7.14', 'german_sideeffects_info'),
    ('7.15', 'german_statistical_info'),
    ('7.16', 'german_dataprotection_info'),
    ('7.17', 'german_aftercare_info'),
    ('7.18', 'german_payment_info'),
    ('7.19', 'german_abort_info'),
    ('7.20', 'german_dataaccess_info'),
    ('7.21', 'german_financing_info'),
    ('7.22', 'german_additional_info'),
    ('8.1.1', 'study_plan_8_1_1'),
    ('8.1.2', 'study_plan_8_1_2'),
    ('8.1.3', 'study_plan_8_1_3'),
    ('8.1.4', 'monocentric'),# property
    ('8.1.5', 'study_plan_8_1_5'),
    ('8.1.6', 'study_plan_8_1_6'),
    ('8.1.7', 'study_plan_8_1_7'),
    ('8.1.8', 'multicentric'),# property
    ('8.1.9', 'study_plan_8_1_9'),
    ('8.1.10', 'study_plan_8_1_10'),
    ('8.1.11', 'study_plan_8_1_11'),
    ('8.1.12', 'study_plan_8_1_12'),
    ('8.1.13', 'study_plan_8_1_13'),
    ('8.1.14', 'study_plan_8_1_14'),
    ('8.1.15', 'study_plan_8_1_15'),
    ('8.1.16', 'study_plan_8_1_16'),
    ('8.1.17', 'study_plan_8_1_17'),
    ('8.1.18', 'study_plan_8_1_18'),
    ('8.1.19', 'study_plan_8_1_19'),
    ('8.1.20', 'study_plan_8_1_20'),
    ('8.1.21', 'study_plan_8_1_21'),
    ('8.1.22', 'study_plan_8_1_22'),
    ('8.2.1', 'study_plan_alpha'),
    ('8.2.2', 'study_plan_power'),
    ('8.2.3', 'study_plan_statalgorithm'),
    ('8.2.4', 'study_plan_multiple_test_correction_algorithm'),
    ('8.2.5', 'study_plan_dropout_ratio'),
    ('8.3.1', 'study_plan_8_3_1'),
    ('8.3.2', 'study_plan_8_3_2'),
    ('8.3.3', 'study_plan_abort_crit'),
    ('8.3.4', 'study_plan_planned_statalgorithm'),
    ('8.4.1', 'study_plan_dataquality_checking'),
    ('8.4.2', 'study_plan_datamanagement'),
    ('8.5.1', 'study_plan_biometric_planning'),
    ('8.5.2', 'study_plan_statistics_implementation'),
    ('8.6.2', 'study_plan_dataprotection_reason'),
    ('8.6.2', 'study_plan_dataprotection_dvr'),
    ('8.6.3', 'study_plan_dataprotection_anonalgoritm'),
    ('9.1', 'submitter_name'),
    ('9.2', 'submitter_organisation'),
    ('9.3', 'submitter_jobtitle'),
    ('9.4.1', 'submitter_is_coordinator'),
    ('9.4.2', 'submitter_is_main_investigator'),
    ('9.4.3', 'submitter_is_sponsor'),
    ('9.4.4', 'submitter_is_authorized_by_sponsor'),
)

_numbers_by_fieldname = {} 

SUBMISSION_FIELD_DATA = []
for number, field_name in _submission_field_data:
    try:
        label = SubmissionForm._meta.get_field(field_name).verbose_name
    except FieldDoesNotExist:
        label = None
    if field_name:
        _numbers_by_fieldname[field_name] = number
    SUBMISSION_FIELD_DATA.append((number, label, field_name))
    
    
def get_number_for_fieldname(name):
    return _numbers_by_fieldname[name]
    
