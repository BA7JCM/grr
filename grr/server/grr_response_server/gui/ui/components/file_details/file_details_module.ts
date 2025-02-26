import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {HexViewModule} from '../data_renderers/hex_view/hex_view_module';
import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {FileDetails} from './file_details';
import {FileDetailsPage} from './file_details_page';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    HexViewModule,
    HumanReadableSizeModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTooltipModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: [FileDetails, FileDetailsPage],
  exports: [FileDetails],
})
export class FileDetailsModule {}
