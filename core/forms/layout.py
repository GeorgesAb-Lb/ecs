# -*- coding: utf-8 -*-
from ecs.core.forms import NotificationForm, ProgressReportNotificationForm, CompletionReportNotificationForm

# ((tab_label1, [(fieldset_legend11, [field111, field112, ..]), (fieldset_legend12, [field121, field122, ..]), ...]),
#  (tab_label2, [(fieldset_legend21, [field211, field212, ..]), (fieldset_legend22, [field221, field222, ..]), ...]),
# )
SUBMISSION_FORM_TABS = (
    (u'Eckdaten', [
        (u'Titel', ['project_title', 'german_project_title', 'eudract_number', 'specialism', 'clinical_phase', 'already_voted',]),
        (u'Art des Projekts', [
            'project_type_non_reg_drug', 'project_type_reg_drug', 'project_type_reg_drug_within_indication', 'project_type_reg_drug_not_within_indication', 
            'project_type_medical_method', 'project_type_medical_device', 'project_type_medical_device_with_ce', 'project_type_medical_device_without_ce',
            'project_type_medical_device_performance_evaluation', 'project_type_basic_research', 'project_type_genetic_study', 'project_type_register',
            'project_type_biobank', 'project_type_retrospective', 'project_type_questionnaire', 'project_type_education_context', 'project_type_misc',
        ]),
        (u'Zentren im Ausland', []),
    ]),
    (u'Prüfungsteilnehmer', [
        (u'Prüfungsteilnehmer', [
            'subject_count', 'subject_minage', 'subject_maxage', 'subject_noncompetents', 'subject_males', 'subject_females', 
            'subject_childbearing', 'subject_duration', 'subject_duration_active', 'subject_duration_controls', 'subject_planned_total_duration',
        ]),
    ]),
    (u'Sponsor', [
        (u'Sponsor', [
            'sponsor_name', 'sponsor_contactname', 'sponsor_address1', 'sponsor_address2', 'sponsor_zip_code', 
            'sponsor_city', 'sponsor_phone', 'sponsor_fax', 'sponsor_email',
            'invoice_differs_from_sponsor',
        ]),
        (u'Rechnungsempfänger', [
            'invoice_name', 'invoice_contactname', 'invoice_address1', 'invoice_address2', 'invoice_zip_code', 
            'invoice_city', 'invoice_phone', 'invoice_fax', 'invoice_email',
            'invoice_uid_verified_level1', 'invoice_uid_verified_level2',
        ]),
    ]),
    (u'AMG', [
        (u'Arzneimittelstudie', ['pharma_checked_substance', 'pharma_reference_substance']),
        (u'AMG', [
            'substance_registered_in_countries', 'substance_preexisting_clinical_tries', 
            'substance_p_c_t_countries', 'substance_p_c_t_phase', 'substance_p_c_t_period', 
            'substance_p_c_t_application_type', 'substance_p_c_t_gcp_rules', 'substance_p_c_t_final_report',
        ]),
    ]),
    (u'MPG', [
        (u'Medizinproduktestudie', ['medtech_checked_product', 'medtech_reference_substance']),    
        (u'MPG', [
            'medtech_product_name', 'medtech_manufacturer', 'medtech_certified_for_exact_indications', 'medtech_certified_for_other_indications', 
            'medtech_ce_symbol', 'medtech_manual_included', 'medtech_technical_safety_regulations', 'medtech_departure_from_regulations',
        ]),
    ]),
    (u'Versicherung', [
        (u'Versicherung', [
            'insurance_name', 'insurance_address_1', 'insurance_phone', 'insurance_contract_number', 'insurance_validity',
        ]),
    ]),
    (u'Massnahmen', [
        (u'Massnahmen', ['additional_therapy_info',]),
    ]),
    (u'Kurzfassung', [
        (u'Kurzfassung', [
            'german_summary', 'german_preclinical_results', 'german_primary_hypothesis', 'german_inclusion_exclusion_crit', 
            'german_ethical_info', 'german_protected_subjects_info', 'german_recruitment_info', 'german_consent_info', 'german_risks_info', 
            'german_benefits_info', 'german_relationship_info', 'german_concurrent_study_info', 'german_sideeffects_info', 
            'german_statistical_info', 'german_dataprotection_info', 'german_aftercare_info', 'german_payment_info', 'german_abort_info', 'german_dataaccess_info',
            'german_financing_info', 'german_additional_info',
        ]),
    ]),
    (u'Biometrie', [
        (u'Biometrie', [
            'study_plan_blind', 'study_plan_observer_blinded', 'study_plan_randomized', 'study_plan_parallelgroups', 'study_plan_controlled', 
            'study_plan_cross_over', 'study_plan_placebo', 'study_plan_factorized', 'study_plan_pilot_project', 'study_plan_equivalence_testing', 
            'study_plan_misc', 'study_plan_number_of_groups', 'study_plan_stratification', 'study_plan_sample_frequency', 'study_plan_primary_objectives',
            'study_plan_null_hypothesis', 'study_plan_alternative_hypothesis', 'study_plan_secondary_objectives',
            'study_plan_alpha', 'study_plan_power', 'study_plan_statalgorithm', 'study_plan_multiple_test_correction_algorithm', 'study_plan_dropout_ratio',
            'study_plan_population_intention_to_treat', 'study_plan_population_per_protocol', 'study_plan_abort_crit', 'study_plan_planned_statalgorithm', 
            'study_plan_dataquality_checking', 'study_plan_datamanagement', 'study_plan_biometric_planning', 'study_plan_statistics_implementation', 
            'study_plan_dataprotection_reason', 'study_plan_dataprotection_dvr', 'study_plan_dataprotection_anonalgoritm', 
        ]),
    ]),
    (u'Unterlagen', []),
    (u'Antragsteller', [
        (u'Antragsteller', [
            'submitter_name', 'submitter_organisation', 'submitter_jobtitle', 'submitter_is_coordinator', 'submitter_is_main_investigator', 'submitter_is_sponsor',
            'submitter_is_authorized_by_sponsor', 'submitter_agrees_to_publishing',
        ]),
    ]),
    (u'Zentrum', []),

# TODO
# The following declaration would fit in nicely, but is not working because
# * fields below are from model Investigator and not Submission
# * the whole tab needs to be repetitive, but FormSet usage is mostly hacked into
#   the template and not declared right now
#
#    (u'Prüfer', [
#        (u'Angaben zur Prüferin/zum Prüfer', [
#            'name', 'organisation',
#            'phone', 'mobile', 'fax', 'email',
#            'jus_practicandi', 'specialist', 'certified', #'', TODO add missing field
#        ]),
#        (u'Geplante Anzahl der Patient/inn/en bzw. Proband/inn/en an dieser Prüfstelle', [
#            'subject_count',
#        ]),
#        (u'Verantwortliche Mitarbeiter/innen an der klinischen Studie (an Ihrer Prüfstelle)', []),
#    ]),

)



NOTIFICATION_FORM_TABS = {}

NOTIFICATION_FORM_TABS[NotificationForm] = [
    (u'Allgemeine Angaben', [
        (u'Allgemeine Angaben', [
            'submission_forms', 'comments',
        ]),
    ]),
    (u'Unterlagen', []),
]

NOTIFICATION_FORM_TABS[CompletionReportNotificationForm] = NOTIFICATION_FORM_TABS[NotificationForm][:1] + [
    (u'Studienstatus', [
        (u'Status', [
            'reason_for_not_started', 'study_aborted', 'completion_date',
        ]),
        (u'Teilnehmer', [
            'recruited_subjects', 'finished_subjects', 'aborted_subjects',
        ]),
        (u'SAE / SUSAR', [
            'SAE_count', 'SUSAR_count',
        ])
    ]),
    (u'Unterlagen', []),
]

NOTIFICATION_FORM_TABS[ProgressReportNotificationForm] = NOTIFICATION_FORM_TABS[NotificationForm][:1] + [
    (u'Studienstatus', [
        (u'Status', [
            'reason_for_not_started', 'runs_till',
        ]),
        (u'Teilnehmer', [
            'recruited_subjects', 'finished_subjects', 'aborted_subjects',
        ]),
        (u'SAE / SUSAR', [
            'SAE_count', 'SUSAR_count',
        ]),
    ]),
    (u'Votum', [
        (u'Verlängerung', [
            'extension_of_vote_requested',
        ]),
    ]),
    (u'Unterlagen', []),
]
