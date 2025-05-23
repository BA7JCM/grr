import {ChangeDetectionStrategy, Component} from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  ValidationErrors,
} from '@angular/forms';

import {ExtFlagsCondition} from '../../components/flow_args_form/collect_multiple_files_form_helpers/ext_flags_condition';
import {
  createLiteralMatchFormGroup,
  fileFinderContentsLiteralMatchConditionToFormValue,
  formValuesToFileFinderContentsLiteralMatchCondition,
} from '../../components/flow_args_form/collect_multiple_files_form_helpers/literal_match_condition';
import {
  createRegexMatchFormGroup,
  formValuesToFileFinderContentsRegexMatchCondition,
  regexMatchConditionFlowArgsToFormValues,
} from '../../components/flow_args_form/collect_multiple_files_form_helpers/regex_match_condition';
import {
  createSizeFormGroup,
  sizeConditionToFormValue,
} from '../../components/flow_args_form/collect_multiple_files_form_helpers/size_condition';
import {
  createTimeRangeFormGroup,
  fileFinderAccessTimeConditionToFormValue,
  fileFinderInodeChangeTimeConditionToFormValue,
  fileFinderModificationTimeConditionToFormValue,
  formValuesToFileFinderAccessTimeCondition,
  formValuesToFileFinderInodeChangeTimeCondition,
  formValuesToFileFinderModificationTimeCondition,
} from '../../components/flow_args_form/collect_multiple_files_form_helpers/time_range_condition';
import {
  ControlValues,
  FlowArgumentForm,
} from '../../components/flow_args_form/form_interface';
import {
  CollectMultipleFilesArgs,
  FileFinderSizeCondition,
} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';

function atLeastOnePathExpression(control: AbstractControl): ValidationErrors {
  for (const c of (control as FormArray).controls) {
    if (isNonNull(c.value) && c.value.trim() !== '') {
      return {};
    }
  }

  return {
    'atLeastOnePathExpressionExpected': true,
  };
}

declare interface Controls {
  pathExpressions: FormArray<FormControl<string>>;
  modificationTime?: ReturnType<typeof createTimeRangeFormGroup>;
  accessTime?: ReturnType<typeof createTimeRangeFormGroup>;
  inodeChangeTime?: ReturnType<typeof createTimeRangeFormGroup>;
  contentsLiteralMatch?: ReturnType<typeof createLiteralMatchFormGroup>;
  contentsRegexMatch?: ReturnType<typeof createRegexMatchFormGroup>;
  size?: ReturnType<typeof createSizeFormGroup>;
  extFlags?: ReturnType<(typeof ExtFlagsCondition)['createFormGroup']>;
}

function makeControls(): Controls {
  return {
    pathExpressions: new FormArray([new FormControl('', {nonNullable: true})], {
      validators: [atLeastOnePathExpression],
    }),
  };
}

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  standalone: false,
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  styleUrls: ['./collect_multiple_files_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesForm extends FlowArgumentForm<
  CollectMultipleFilesArgs,
  Controls
> {
  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    const allResults: CollectMultipleFilesArgs = {
      pathExpressions: formState.pathExpressions,
      modificationTime:
        formState.modificationTime &&
        formValuesToFileFinderModificationTimeCondition(
          formState.modificationTime,
        ),
      accessTime:
        formState.accessTime &&
        formValuesToFileFinderAccessTimeCondition(formState.accessTime),
      inodeChangeTime:
        formState.inodeChangeTime &&
        formValuesToFileFinderInodeChangeTimeCondition(
          formState.inodeChangeTime,
        ),
      contentsLiteralMatch:
        formState.contentsLiteralMatch &&
        formValuesToFileFinderContentsLiteralMatchCondition(
          formState.contentsLiteralMatch,
        ),
      contentsRegexMatch:
        formState.contentsRegexMatch &&
        formValuesToFileFinderContentsRegexMatchCondition(
          formState.contentsRegexMatch,
        ),
      size: formState.size as FileFinderSizeCondition,
      extFlags: formState.extFlags,
    };

    let trimmedResults: CollectMultipleFilesArgs = {};
    for (const [argKey, argValue] of Object.entries(allResults)) {
      if (argValue != null) {
        trimmedResults = {...trimmedResults, [argKey]: argValue};
      }
    }
    return trimmedResults;
  }

  readonly client$;

  constructor(private readonly clientPageGlobalStore: ClientPageGlobalStore) {
    super();
    this.client$ = this.clientPageGlobalStore.selectedClient$;
  }

  override resetFlowArgs(flowArgs: CollectMultipleFilesArgs): void {
    while (
      (flowArgs.pathExpressions?.length ?? 0) >
      this.controls.pathExpressions.length
    ) {
      this.addPathExpression();
    }

    if (flowArgs.contentsRegexMatch) {
      this.addRegexMatchCondition();
    }

    if (flowArgs.contentsLiteralMatch) {
      this.addLiteralMatchCondition();
    }

    if (flowArgs.modificationTime) {
      this.addModificationTimeCondition();
    }

    if (flowArgs.accessTime) {
      this.addAccessTimeCondition();
    }

    if (flowArgs.inodeChangeTime) {
      this.addInodeChangeTimeCondition();
    }

    if (flowArgs.size) {
      this.addSizeCondition();
    }

    if (flowArgs.extFlags) {
      this.addExtFlagsCondition();
    }

    super.resetFlowArgs(flowArgs);
  }

  override convertFlowArgsToFormState(
    flowArgs: CollectMultipleFilesArgs,
  ): ControlValues<Controls> {
    return {
      pathExpressions: flowArgs.pathExpressions?.length
        ? [...flowArgs.pathExpressions]
        : [''],
      contentsRegexMatch: regexMatchConditionFlowArgsToFormValues(
        flowArgs.contentsRegexMatch,
      ),
      contentsLiteralMatch: fileFinderContentsLiteralMatchConditionToFormValue(
        flowArgs.contentsLiteralMatch,
      ),
      modificationTime: fileFinderModificationTimeConditionToFormValue(
        flowArgs.modificationTime,
      ),
      accessTime: fileFinderAccessTimeConditionToFormValue(flowArgs.accessTime),
      inodeChangeTime: fileFinderInodeChangeTimeConditionToFormValue(
        flowArgs.inodeChangeTime,
      ),
      size: sizeConditionToFormValue(flowArgs.size),
      extFlags: flowArgs.extFlags,
    };
  }

  addPathExpression() {
    this.controls.pathExpressions.push(new FormControl());
  }

  removePathExpression(index: number) {
    this.controls.pathExpressions.removeAt(index);
  }

  // Literal match condition.
  addLiteralMatchCondition() {
    this.form.addControl('contentsLiteralMatch', createLiteralMatchFormGroup());
  }

  removeLiteralMatchCondition() {
    this.form.removeControl('contentsLiteralMatch');
  }

  // Regex match condition.
  addRegexMatchCondition() {
    this.form.addControl('contentsRegexMatch', createRegexMatchFormGroup());
  }

  removeRegexMatchCondition() {
    this.form.removeControl('contentsRegexMatch');
  }

  // Modification time condition.
  addModificationTimeCondition() {
    this.form.addControl('modificationTime', createTimeRangeFormGroup());
  }

  removeModificationTimeCondition() {
    this.form.removeControl('modificationTime');
  }

  // Access time condition.
  addAccessTimeCondition() {
    this.form.addControl('accessTime', createTimeRangeFormGroup());
  }

  removeAccessTimeCondition() {
    this.form.removeControl('accessTime');
  }

  // Inode change time condition.
  addInodeChangeTimeCondition() {
    this.form.addControl('inodeChangeTime', createTimeRangeFormGroup());
  }

  removeInodeChangeTimeCondition() {
    this.form.removeControl('inodeChangeTime');
  }

  // File size condition.
  addSizeCondition() {
    this.form.addControl('size', createSizeFormGroup());
  }

  removeSizeCondition() {
    this.form.removeControl('size');
  }

  // Extended file flags condition.
  addExtFlagsCondition() {
    this.form.addControl('extFlags', ExtFlagsCondition.createFormGroup());
  }

  removeExtFlagsCondition() {
    this.form.removeControl('extFlags');
  }
}
