import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectModule} from '@angular/material/select';
import {RouterModule} from '@angular/router';

import {FlowDetailsModule} from '../flow_details/module';
import {InfiniteListModule} from '../helpers/infinite_list/infinite_list_module';
import {TimestampModule} from '../timestamp/module';

import {FlowList} from './flow_list';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    FlowDetailsModule,
    FormsModule,
    InfiniteListModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    ReactiveFormsModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: [FlowList],
  exports: [FlowList],
})
export class FlowListModule {}
